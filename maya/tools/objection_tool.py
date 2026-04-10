from __future__ import annotations

import subprocess

from .registry import register_tool


@register_tool(sandbox_execution=True)
def objection_run_command(package_name: str, command: str, timeout: str = "90") -> dict:
    """Run a single Objection command against package."""
    proc = subprocess.run(
        ["objection", "-g", package_name, "explore", "-c", command],
        text=True,
        capture_output=True,
        timeout=int(timeout),
    )
    return {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode}


@register_tool(sandbox_execution=True)
def objection_explore(package_name: str) -> dict:
    """Show available Objection command context."""
    return objection_run_command(package_name=package_name, command="help")
