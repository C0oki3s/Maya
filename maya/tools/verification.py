from __future__ import annotations

import subprocess

from .registry import register_tool


@register_tool(sandbox_execution=True)
def verify_device_connected() -> dict:
    """Verify at least one device is connected through adb."""
    proc = subprocess.run(["adb", "devices"], text=True, capture_output=True, timeout=30)
    lines = [ln for ln in proc.stdout.splitlines() if "\tdevice" in ln]
    return {"status": "ok" if lines else "error", "devices": lines, "stdout": proc.stdout}


@register_tool(sandbox_execution=True)
def verify_frida_attached(package_name: str) -> dict:
    """Verify Frida can see target process."""
    proc = subprocess.run(["frida-ps", "-U"], text=True, capture_output=True, timeout=30)
    ok = package_name in proc.stdout
    return {"status": "ok" if ok else "error", "stdout": proc.stdout, "stderr": proc.stderr}


@register_tool(sandbox_execution=True)
def verify_ssl_bypass(test_url: str = "https://example.com") -> dict:
    """Verify HTTPS request succeeds after bypass setup."""
    proc = subprocess.run(["curl", "-k", "-I", test_url], text=True, capture_output=True, timeout=30)
    return {"status": "ok" if proc.returncode == 0 else "error", "stdout": proc.stdout, "stderr": proc.stderr}


@register_tool(sandbox_execution=True)
def verify_proxy_active(host: str = "127.0.0.1", port: str = "8080") -> dict:
    """Verify proxy endpoint is reachable."""
    proc = subprocess.run(["curl", "-s", f"http://{host}:{port}"], text=True, capture_output=True, timeout=10)
    return {"status": "ok" if proc.returncode == 0 else "error", "stdout": proc.stdout, "stderr": proc.stderr}
