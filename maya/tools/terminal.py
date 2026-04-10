from __future__ import annotations

import subprocess
from pathlib import Path

from .registry import register_tool


@register_tool(sandbox_execution=True)
def terminal_execute(command: str, timeout: str = "60") -> dict:
    """Execute a shell command and return stdout/stderr/exit_code."""
    timeout_s = int(timeout)
    proc = subprocess.run(  # noqa: S602
        command,
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout_s,
    )
    return {
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "exit_code": proc.returncode,
    }


@register_tool(sandbox_execution=True)
def python_execute(code: str, timeout: str = "60") -> dict:
    """Execute Python code through python -c and return output."""
    proc = subprocess.run(
        ["python", "-c", code],
        text=True,
        capture_output=True,
        timeout=int(timeout),
    )
    return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}


@register_tool(sandbox_execution=True)
def file_read(path: str) -> dict:
    """Read text file content from disk."""
    p = Path(path)
    return {"path": str(p), "content": p.read_text(encoding="utf-8")}


@register_tool(sandbox_execution=True)
def file_write(path: str, content: str) -> dict:
    """Write text file content to disk."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return {"status": "ok", "path": str(p)}


@register_tool(sandbox_execution=True)
def semgrep_scan(path: str, timeout: str = "180") -> dict:
    """Run semgrep against path using default rules."""
    proc = subprocess.run(
        ["semgrep", "--config", "auto", path],
        text=True,
        capture_output=True,
        timeout=int(timeout),
    )
    return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}


@register_tool(sandbox_execution=True)
def nuclei_scan(target: str, timeout: str = "180") -> dict:
    """Run nuclei against a target URL or host."""
    proc = subprocess.run(
        ["nuclei", "-u", target],
        text=True,
        capture_output=True,
        timeout=int(timeout),
    )
    return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}
