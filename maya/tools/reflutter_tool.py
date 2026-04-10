from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .registry import register_tool

_SIGNER_JAR = Path(__file__).resolve().parent.parent.parent / "assets" / "signer" / "uber-apk-signer-1.3.0.jar"


def _adb_base_command() -> list[str]:
    socket = os.environ.get("ADB_SERVER_SOCKET")
    if socket:
        return ["adb", "-L", socket]
    return ["adb"]


@register_tool(sandbox_execution=True)
def reflutter_analyze(apk_path: str) -> dict:
    """Analyze Flutter APK using reflutter."""
    try:
        proc = subprocess.run(["reflutter", apk_path], text=True, capture_output=True, timeout=120)
        return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}
    except Exception as exc:
        return {"error": str(exc)}


@register_tool(sandbox_execution=True)
def reflutter_patch_and_install(
    apk_path: str,
    proxy_host: str = "127.0.0.1",
    proxy_port: str = "8083",
    timeout: str = "300",
) -> dict:
    """Patch a Flutter APK with reFlutter, sign it with uber-apk-signer,
    set system-wide proxy to port 8083, and install on device.

    Full pipeline: reflutter patch -> sign -> set proxy 8083 -> adb install."""
    apk = Path(apk_path)
    if not apk.exists():
        return {"error": f"APK not found: {apk_path}"}
    if not _SIGNER_JAR.exists():
        return {"error": f"Signer JAR not found: {_SIGNER_JAR}"}

    timeout_s = int(timeout)

    # Step 1: Patch with reFlutter
    try:
        proc = subprocess.run(
            ["reflutter", str(apk)],
            text=True,
            capture_output=True,
            timeout=min(timeout_s, 180),
        )
        if proc.returncode != 0:
            return {
                "error": f"reFlutter patch failed: {proc.stderr}",
                "step": "reflutter_patch",
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
    except Exception as exc:
        return {"error": str(exc), "step": "reflutter_patch"}

    # reFlutter outputs release.RE.apk in the same directory
    patched_apk = apk.parent / "release.RE.apk"
    if not patched_apk.exists():
        # Some versions use the original name with .RE suffix
        alt = apk.with_suffix(".RE.apk")
        if alt.exists():
            patched_apk = alt
        else:
            return {
                "error": "Patched APK not found after reFlutter. Check reflutter output.",
                "step": "reflutter_patch",
                "stdout": proc.stdout,
            }

    # Step 2: Sign with uber-apk-signer
    try:
        sign_proc = subprocess.run(
            ["java", "-jar", str(_SIGNER_JAR), "--apks", str(patched_apk), "--overwrite"],
            text=True,
            capture_output=True,
            timeout=120,
        )
        if sign_proc.returncode != 0:
            return {
                "error": f"Signing failed: {sign_proc.stderr}",
                "step": "sign",
                "stdout": sign_proc.stdout,
                "stderr": sign_proc.stderr,
            }
    except Exception as exc:
        return {"error": str(exc), "step": "sign"}

    # Step 3: Set system-wide proxy to 8083 on device
    try:
        proxy_cmd = _adb_base_command() + [
            "shell",
            "settings",
            "put",
            "global",
            "http_proxy",
            f"{proxy_host}:{proxy_port}",
        ]
        subprocess.run(proxy_cmd, text=True, capture_output=True, timeout=30)
    except Exception as exc:
        return {"error": f"Proxy setup failed: {exc}", "step": "proxy_setup"}

    # Step 4: Install signed APK
    try:
        install_cmd = _adb_base_command() + ["install", "-r", str(patched_apk)]
        install_proc = subprocess.run(
            install_cmd,
            text=True,
            capture_output=True,
            timeout=120,
        )
        if install_proc.returncode != 0:
            return {
                "error": f"Install failed: {install_proc.stderr}",
                "step": "install",
                "stdout": install_proc.stdout,
                "stderr": install_proc.stderr,
            }
    except Exception as exc:
        return {"error": str(exc), "step": "install"}

    return {
        "status": "ok",
        "patched_apk": str(patched_apk),
        "signed": True,
        "proxy": f"{proxy_host}:{proxy_port}",
        "installed": True,
        "reflutter_stdout": proc.stdout[:2000],
    }


@register_tool(sandbox_execution=True)
def flutter_frida_hooks(package_name: str, timeout: str = "90") -> dict:
    """Inject lightweight flutter hook script through Frida."""
    script = "Java.perform(function(){ send('flutter-hooks-ready'); });"
    from .frida_tool import frida_run_script

    return frida_run_script(package_name=package_name, script=script, timeout=timeout)
