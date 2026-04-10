from __future__ import annotations

import asyncio
import importlib
import json
import os
import subprocess
from pathlib import Path

import requests

try:
    websockets = importlib.import_module("websockets")
except Exception:  # noqa: BLE001
    websockets = None

from .registry import register_tool


def _adb_base_command() -> list[str]:
    # Uses host ADB server when ADB_SERVER_SOCKET is provided.
    socket = os.environ.get("ADB_SERVER_SOCKET")
    if socket:
        return ["adb", "-L", socket]
    return ["adb"]


@register_tool(sandbox_execution=True)
def device_list() -> dict:
    """List connected Android devices via adb devices."""
    cmd = _adb_base_command() + ["devices"]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=30)
    return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}


@register_tool(sandbox_execution=True)
def device_shell(command: str, timeout: str = "60") -> dict:
    """Execute shell command on connected Android device."""
    timeout_s = int(timeout)
    cmd = _adb_base_command() + ["shell", command]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout_s)
    return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}


@register_tool(sandbox_execution=True)
def device_install_app(app_path: str, timeout: str = "120") -> dict:
    """Install an APK onto connected Android device."""
    cmd = _adb_base_command() + ["install", "-r", app_path]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=int(timeout))
    return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}


@register_tool(sandbox_execution=True)
def device_uninstall_app(package_name: str, timeout: str = "60") -> dict:
    """Uninstall Android package from connected device."""
    cmd = _adb_base_command() + ["uninstall", package_name]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=int(timeout))
    return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}


@register_tool(sandbox_execution=True)
def device_pull_file(remote_path: str, local_path: str, timeout: str = "120") -> dict:
    """Pull file from device to local path."""
    out = Path(local_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = _adb_base_command() + ["pull", remote_path, str(out)]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=int(timeout))
    return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode, "path": str(out)}


@register_tool(sandbox_execution=True)
def device_push_file(local_path: str, remote_path: str, timeout: str = "120") -> dict:
    """Push file from local path to device."""
    cmd = _adb_base_command() + ["push", local_path, remote_path]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=int(timeout))
    return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}


@register_tool(sandbox_execution=True)
def device_get_app_info(package_name: str, timeout: str = "60") -> dict:
    """Get package info from device package manager."""
    return device_shell(command=f"dumpsys package {package_name}", timeout=timeout)


@register_tool(sandbox_execution=True)
def device_dump_app_data(package_name: str, platform: str = "android", timeout: str = "120") -> dict:
    """Dump app data with platform-aware logic (android/ios)."""
    if platform == "ios":
        cmd = [
            "ssh",
            "root@localhost",
            "tar",
            "-czf",
            f"/tmp/{package_name}.tar.gz",  # noqa: S108
            f"/var/mobile/Containers/Data/Application/{package_name}",
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=int(timeout))
        return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode, "platform": "ios"}
    return device_shell(
        command=f"su -c 'tar -czf /sdcard/{package_name}.tar.gz /data/data/{package_name}'", timeout=timeout
    )


@register_tool(sandbox_execution=True)
def device_start_frida_server(binary_path: str = "/data/local/tmp/frida-server", timeout: str = "60") -> dict:
    """Start frida-server on Android device if present."""
    return device_shell(command=f"su -c '{binary_path} -D &'", timeout=timeout)


@register_tool(sandbox_execution=True)
def companion_app_command(command: str, params: str = "{}", timeout: str = "30") -> dict:
    """Send command to companion app bridge endpoint."""
    payload = {"id": "cmd_local", "command": command, "params": json.loads(params or "{}")}
    timeout_s = int(timeout)

    ws_url = os.environ.get("COMPANION_WS_URL", "ws://127.0.0.1:9999/command")
    if websockets is not None:

        async def _send_ws() -> dict:
            async with websockets.connect(ws_url, open_timeout=timeout_s, close_timeout=timeout_s) as ws:
                await ws.send(json.dumps(payload))
                msg = await ws.recv()
                try:
                    return json.loads(msg)
                except Exception:
                    return {"raw": msg}

        try:
            return {"status": "ok", "response": asyncio.run(_send_ws())}
        except Exception:  # noqa: S110
            pass  # fall through to HTTP

    host = os.environ.get("COMPANION_HTTP_URL", "http://127.0.0.1:9999/command")
    r = requests.post(host, json=payload, timeout=timeout_s)
    return {
        "status": "ok",
        "response": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text,
    }


@register_tool(sandbox_execution=True)
def ios_decrypt_binary(bundle_id: str, timeout: str = "120") -> dict:
    """Best-effort iOS binary decrypt command wrapper."""
    proc = subprocess.run(
        ["ssh", "root@localhost", "clutch", "-d", bundle_id], text=True, capture_output=True, timeout=int(timeout)
    )
    return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}


@register_tool(sandbox_execution=True)
def ios_dump_keychain(timeout: str = "90") -> dict:
    """Dump iOS keychain entries using keychain-dumper if available."""
    proc = subprocess.run(
        ["ssh", "root@localhost", "keychain-dumper"], text=True, capture_output=True, timeout=int(timeout)
    )
    return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}


@register_tool(sandbox_execution=True)
def device_set_proxy(host: str = "127.0.0.1", port: str = "8080", timeout: str = "30") -> dict:
    """Set system-wide HTTP proxy on Android device via adb settings."""
    try:
        cmd = _adb_base_command() + ["shell", "settings", "put", "global", "http_proxy", f"{host}:{port}"]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=int(timeout))
        return {
            "status": "ok",
            "proxy": f"{host}:{port}",
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
        }
    except Exception as exc:
        return {"error": str(exc)}


@register_tool(sandbox_execution=True)
def device_clear_proxy(timeout: str = "30") -> dict:
    """Remove system-wide HTTP proxy from Android device."""
    try:
        cmd = _adb_base_command() + ["shell", "settings", "put", "global", "http_proxy", ":0"]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=int(timeout))
        return {"status": "ok", "stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}
    except Exception as exc:
        return {"error": str(exc)}
