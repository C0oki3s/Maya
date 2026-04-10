from __future__ import annotations

import importlib
import json
import os
import re
import shlex
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

try:
    frida = importlib.import_module("frida")
except Exception:  # noqa: BLE001
    frida = None

app = FastAPI(title="maya-tool-server")


class ExecuteRequest(BaseModel):
    agent_id: str
    tool_name: str
    kwargs: dict[str, Any]


_AGENT_SESSIONS: dict[str, dict[str, Any]] = {}


class FridaSessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}

    def _device(self):
        if frida is None:
            return None
        host = os.environ.get("FRIDA_HOST")
        if host:
            return frida.get_device_manager().add_remote_device(host)
        return frida.get_usb_device(timeout=5)

    def attach(self, agent_id: str, package_name: str) -> dict[str, Any]:
        device = self._device()
        if device is None:
            self._sessions[agent_id] = {
                "mode": "cli",
                "package_name": package_name,
                "scripts": [],
            }
            return {"status": "ok", "mode": "cli", "package_name": package_name}

        pid = device.spawn([package_name])
        session = device.attach(pid)
        device.resume(pid)
        self._sessions[agent_id] = {
            "mode": "python",
            "device": device,
            "session": session,
            "pid": pid,
            "package_name": package_name,
            "scripts": [],
        }
        return {"status": "ok", "mode": "python", "pid": pid, "package_name": package_name}

    def run_script(self, agent_id: str, package_name: str, script: str) -> dict[str, Any]:
        session_data = self._sessions.get(agent_id)
        if not session_data or session_data.get("package_name") != package_name:
            self.attach(agent_id, package_name)
            session_data = self._sessions.get(agent_id)

        if session_data and session_data.get("mode") == "python":
            session = session_data["session"]
            out: list[str] = []

            frida_script = session.create_script(script)

            def _on_message(msg, _data):  # type: ignore[no-untyped-def]
                out.append(json.dumps(msg))

            frida_script.on("message", _on_message)
            frida_script.load()
            session_data["scripts"].append(frida_script)
            return {"status": "ok", "mode": "python", "stdout": "\n".join(out), "stderr": "", "exit_code": 0}

        with NamedTemporaryFile(mode="w", suffix=".js", delete=False, encoding="utf-8") as tmp:
            tmp.write(script)
            script_path = Path(tmp.name)
        try:
            # Security: Validate package name to prevent command injection
            safe_package = _validate_package_name(package_name)
            host = os.environ.get("FRIDA_HOST")
            if host:
                cmd = ["frida", "-H", host, "-n", safe_package, "-l", str(script_path), "--no-pause", "-q"]
            else:
                cmd = ["frida", "-U", "-n", safe_package, "-l", str(script_path), "--no-pause", "-q"]
            proc = subprocess.run(cmd, text=True, capture_output=True, timeout=90, check=False)
            return {
                "status": "ok",
                "mode": "cli",
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "exit_code": proc.returncode,
            }
        finally:
            script_path.unlink(missing_ok=True)

    def detach(self, agent_id: str) -> dict[str, Any]:
        session_data = self._sessions.pop(agent_id, None)
        if not session_data:
            return {"status": "ok", "message": "no session"}

        if session_data.get("mode") == "python":
            for script in session_data.get("scripts", []):
                try:  # noqa: SIM105
                    script.unload()
                except Exception:  # noqa: S110
                    pass  # best-effort cleanup
            try:  # noqa: SIM105
                session_data["session"].detach()
            except Exception:  # noqa: S110
                pass  # best-effort cleanup
        return {"status": "ok"}


_FRIDA_MANAGER = FridaSessionManager()

# Security: Workspace root for path validation
_WORKSPACE_ROOT = Path("/workspace").resolve()


def _validate_package_name(package: str) -> str:
    """Validate Android package name to prevent command injection."""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$", package):
        raise ValueError(f"Invalid package name: {package}")
    return package


def _validate_path(path: str) -> Path:
    """Validate file path is within workspace to prevent path traversal."""
    # Security: Reject paths with suspicious characters
    if ".." in path or path.startswith("/") and not path.startswith("/workspace"):
        raise ValueError(f"Invalid path: {path}")
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(_WORKSPACE_ROOT)
    except ValueError:
        raise ValueError(f"Path outside workspace: {path}") from None
    return resolved


def _validate_command(cmd: str) -> None:
    """Validate command is in the allowed list to prevent arbitrary execution."""
    # Security: Whitelist of allowed commands in sandbox
    allowed_commands = {
        "adb", "aapt", "aapt2", "apktool", "jadx", "jarsigner",
        "keytool", "zipalign", "d8", "baksmali", "smali",
        "objection", "frida", "frida-ps", "frida-trace", "drozer",
        "curl", "wget", "grep", "find", "cat", "ls", "pwd",
        "chmod", "chown", "mkdir", "rm", "cp", "mv",
        "python", "python3", "pip", "pip3", "node", "npm",
        "git", "docker", "java", "javac",
    }
    cmd_base = Path(cmd).name  # Get just the command name, strip path
    if cmd_base not in allowed_commands:
        raise ValueError(f"Command not allowed: {cmd_base}")


def _auth_ok(authorization: str | None) -> bool:
    token = os.environ.get("SANDBOX_AUTH_TOKEN")
    if not token:
        return True
    if not authorization or not authorization.startswith("Bearer "):
        return False
    return authorization.split(" ", 1)[1] == token


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/register_agent")
def register_agent(payload: dict[str, str], authorization: str | None = Header(default=None)) -> dict[str, str]:
    if not _auth_ok(authorization):
        raise HTTPException(status_code=401, detail="unauthorized")
    agent_id = payload.get("agent_id", "")
    _AGENT_SESSIONS.setdefault(agent_id, {})
    return {"status": "ok", "agent_id": agent_id}


@app.post("/execute")
def execute(req: ExecuteRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not _auth_ok(authorization):
        raise HTTPException(status_code=401, detail="unauthorized")

    _AGENT_SESSIONS.setdefault(req.agent_id, {})
    try:
        result = _dispatch_tool(req.agent_id, req.tool_name, req.kwargs)
        return {"result": result, "error": None}
    except (ValueError, FileNotFoundError) as exc:
        # Security: Only expose safe exception types with limited details
        error_msg = f"{type(exc).__name__}: {str(exc)[:100]}"
        return {"result": None, "error": error_msg}
    except Exception:  # noqa: BLE001
        # Security: Don't expose internal exception details
        return {"result": None, "error": "Internal error occurred"}


def _dispatch_tool(agent_id: str, tool_name: str, kwargs: dict[str, Any]) -> dict[str, Any]:
    if tool_name == "terminal_execute":
        command = kwargs["command"]
        timeout = int(kwargs.get("timeout", "60"))
        # Security: Parse command safely and validate allowed commands
        cmd_parts = shlex.split(command) if isinstance(command, str) else command
        if not isinstance(cmd_parts, list) or len(cmd_parts) == 0:
            raise ValueError("Invalid command format")
        # Validate the base command is safe (whitelist approach)
        _validate_command(cmd_parts[0])
        proc = subprocess.run(cmd_parts, text=True, capture_output=True, timeout=timeout, check=False, shell=False)
        return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}

    if tool_name == "python_execute":
        code = kwargs["code"]
        timeout = int(kwargs.get("timeout", "60"))
        # Security: Write code to temporary file instead of passing via -c to avoid injection
        with NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(code)
            code_path = Path(tmp.name)
        try:
            proc = subprocess.run(["python3", str(code_path)], text=True, capture_output=True, timeout=timeout, check=False, shell=False)
            return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}
        finally:
            code_path.unlink(missing_ok=True)

    if tool_name == "frida_attach":
        return _FRIDA_MANAGER.attach(agent_id=agent_id, package_name=kwargs["package_name"])

    if tool_name == "frida_detach":
        return _FRIDA_MANAGER.detach(agent_id=agent_id)

    if tool_name == "frida_spawn":
        # Spawn semantics are handled by attach() in python mode.
        return _FRIDA_MANAGER.attach(agent_id=agent_id, package_name=kwargs["package_name"])

    if tool_name == "frida_run_script":
        package_name = kwargs["package_name"]
        script = kwargs["script"]
        return _FRIDA_MANAGER.run_script(agent_id=agent_id, package_name=package_name, script=script)

    if tool_name == "file_read":
        # Security: Validate path to prevent traversal attacks
        path_str = str(kwargs["path"])
        path = _validate_path(path_str)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path_str}")
        if not path.is_file():
            raise ValueError(f"Not a file: {path_str}")
        return {"content": path.read_text(encoding="utf-8")}

    if tool_name == "file_write":
        # Security: Validate path to prevent traversal attacks
        path_str = str(kwargs["path"])
        path = _validate_path(path_str)
        content = str(kwargs["content"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"status": "ok", "path": str(path)}

    if tool_name.startswith("caido_"):
        caido_module = importlib.import_module("maya.tools.caido_tool")
        caido_fn = getattr(caido_module, tool_name, None)
        if caido_fn is None:
            return {"status": "error", "message": f"unknown caido tool: {tool_name}"}
        return caido_fn(**kwargs)

    return {"status": "unhandled", "tool": tool_name, "kwargs": json.dumps(kwargs)}
