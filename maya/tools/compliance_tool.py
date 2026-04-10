from __future__ import annotations

import os
import subprocess
from pathlib import Path
from time import time

from .registry import register_tool

# Resolve asset paths relative to project root
_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "frida-scripts"

# Mapping of test case IDs to Frida script paths
_COMPLIANCE_SCRIPTS: dict[str, dict] = {
    "secure_boot": {
        "name": "Trusted Device / Secure Boot Verification",
        "script": _ASSETS_DIR / "bypass" / "secure_boot_check.js",
        "category": "device_integrity",
        "description": "Verify the app runs only on trusted devices with secure boot enabled.",
    },
    "emulator_detection": {
        "name": "Emulator / Virtualization Detection",
        "script": _ASSETS_DIR / "bypass" / "emulator_detection.js",
        "category": "device_integrity",
        "description": "Ensure the app detects and prevents execution in a virtualization environment.",
    },
    "root_detection": {
        "name": "Root Detection Enforcement",
        "script": _ASSETS_DIR / "bypass" / "root_detection_universal.js",
        "category": "device_integrity",
        "description": "Ensure the app enforces non-rooted/non-jailbroken device usage.",
    },
    "rasp_detection": {
        "name": "Code Obfuscation, RASP & Anti-Debugging",
        "script": _ASSETS_DIR / "enumerate" / "rasp_detection.js",
        "category": "code_protection",
        "description": "Check for code obfuscation, RASP, and anti-debugging techniques.",
    },
    "debug_detection": {
        "name": "Anti-Debug Protection",
        "script": _ASSETS_DIR / "bypass" / "debug_detection.js",
        "category": "code_protection",
        "description": "Check anti-debugging techniques and bypass resistance.",
    },
    "code_tampering": {
        "name": "Code Tampering Resistance",
        "script": _ASSETS_DIR / "bypass" / "integrity_check.js",
        "category": "code_protection",
        "description": "Check for code tampering detection and resistance.",
    },
    "crypto_keys": {
        "name": "AES-256 Encryption Verification",
        "script": _ASSETS_DIR / "extract" / "crypto_keys.js",
        "category": "encryption",
        "description": "Verify AES-256 encryption for data at rest and in transit.",
    },
    "data_containerization": {
        "name": "Data Isolation & Containerization",
        "script": _ASSETS_DIR / "extract" / "data_containerization_check.js",
        "category": "encryption",
        "description": "Confirm that data is isolated using containerization methods.",
    },
    "tls_version": {
        "name": "TLS 1.3+ Communication Verification",
        "script": _ASSETS_DIR / "extract" / "tls_version_check.js",
        "category": "transport_security",
        "description": "Verify all communications are encrypted using TLS 1.3 or higher.",
    },
    "ssl_pinning": {
        "name": "Certificate Pinning Validation",
        "script": _ASSETS_DIR / "bypass" / "ssl_pinning_universal.js",
        "category": "transport_security",
        "description": "Validate certificate pinning to prevent MITM attacks.",
    },
}

# Category groupings for selective runs
_CATEGORIES: dict[str, list[str]] = {
    "device_integrity": ["secure_boot", "emulator_detection", "root_detection"],
    "code_protection": ["rasp_detection", "debug_detection", "code_tampering"],
    "encryption": ["crypto_keys", "data_containerization", "tls_version", "ssl_pinning"],
    "transport_security": ["tls_version", "ssl_pinning"],
}


def _frida_cmd(package_name: str, script_path: str) -> list[str]:
    """Build frida command with proper target args."""
    frida_host = os.environ.get("FRIDA_HOST")
    if frida_host:
        return ["frida", "-H", frida_host, "-n", package_name, "-l", script_path, "--no-pause", "-q"]
    return ["frida", "-U", "-n", package_name, "-l", script_path, "--no-pause", "-q"]


def _run_script(package_name: str, script_path: Path, timeout: int = 90) -> dict:
    """Execute a single Frida script and capture output."""
    if not script_path.exists():
        return {"error": f"Script not found: {script_path}"}

    cmd = _frida_cmd(package_name, str(script_path))
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Script timed out after {timeout}s", "exit_code": -1}
    except Exception as exc:
        return {"error": str(exc)}


@register_tool(sandbox_execution=True)
def run_compliance_scan(
    package_name: str,
    test_cases: str = "all",
    timeout: str = "90",
) -> dict:
    """Run automated security compliance checks against a target app.

    Executes Frida-based compliance test scripts covering device integrity,
    code protection, encryption, and transport security. Use test_cases='all'
    for full scan, or specify a category: device_integrity, code_protection,
    encryption, transport_security. You can also specify comma-separated
    individual test IDs: secure_boot,root_detection,ssl_pinning."""
    timeout_s = int(timeout)
    start = time()

    # Determine which tests to run
    if test_cases == "all":
        selected = list(_COMPLIANCE_SCRIPTS.keys())
    elif test_cases in _CATEGORIES:
        selected = _CATEGORIES[test_cases]
    else:
        selected = [t.strip() for t in test_cases.split(",") if t.strip() in _COMPLIANCE_SCRIPTS]

    if not selected:
        return {
            "error": f"No valid test cases found for: {test_cases}. "
            f"Valid options: all, {', '.join(_CATEGORIES.keys())}, "
            f"or individual: {', '.join(_COMPLIANCE_SCRIPTS.keys())}"
        }

    results: dict[str, dict] = {}
    passed = 0
    failed = 0
    errors = 0

    for test_id in selected:
        spec = _COMPLIANCE_SCRIPTS[test_id]
        result = _run_script(package_name, spec["script"], timeout=timeout_s)

        status = "error"
        if "error" in result:
            errors += 1
            status = "error"
        elif result.get("exit_code", -1) == 0:
            passed += 1
            status = "executed"
        else:
            failed += 1
            status = "execution_failed"

        results[test_id] = {
            "name": spec["name"],
            "category": spec["category"],
            "description": spec["description"],
            "status": status,
            "output": result.get("stdout", "")[:3000],
            "stderr": result.get("stderr", "")[:1000],
            "exit_code": result.get("exit_code"),
        }

    elapsed = round(time() - start, 2)

    return {
        "status": "ok",
        "package_name": package_name,
        "test_cases_requested": test_cases,
        "total_tests": len(selected),
        "executed": passed,
        "execution_failed": failed,
        "errors": errors,
        "elapsed_seconds": elapsed,
        "results": results,
        "summary": _build_summary(results),
    }


@register_tool(sandbox_execution=True)
def run_compliance_check(
    package_name: str,
    check_name: str,
    timeout: str = "90",
) -> dict:
    """Run a single compliance check against a target app.

    Available checks: secure_boot, emulator_detection, root_detection,
    rasp_detection, debug_detection, code_tampering, crypto_keys,
    data_containerization, tls_version, ssl_pinning."""
    if check_name not in _COMPLIANCE_SCRIPTS:
        return {"error": f"Unknown check: {check_name}. Available: {', '.join(_COMPLIANCE_SCRIPTS.keys())}"}

    spec = _COMPLIANCE_SCRIPTS[check_name]
    result = _run_script(package_name, spec["script"], timeout=int(timeout))

    return {
        "status": "ok" if "error" not in result else "error",
        "check": check_name,
        "name": spec["name"],
        "category": spec["category"],
        "description": spec["description"],
        "output": result.get("stdout", "")[:5000],
        "stderr": result.get("stderr", "")[:2000],
        "exit_code": result.get("exit_code"),
        "error": result.get("error"),
    }


@register_tool(sandbox_execution=False)
def list_compliance_checks() -> dict:
    """List all available compliance test cases and categories."""
    checks = {}
    for test_id, spec in _COMPLIANCE_SCRIPTS.items():
        checks[test_id] = {
            "name": spec["name"],
            "category": spec["category"],
            "description": spec["description"],
            "script": spec["script"].name,
        }

    return {
        "status": "ok",
        "total_checks": len(checks),
        "categories": {cat: ids for cat, ids in _CATEGORIES.items()},
        "checks": checks,
    }


def _build_summary(results: dict[str, dict]) -> str:
    """Build a human-readable compliance summary."""
    lines = ["# Compliance Scan Summary", ""]

    by_category: dict[str, list[tuple[str, dict]]] = {}
    for test_id, result in results.items():
        cat = result["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append((test_id, result))

    for category, items in sorted(by_category.items()):
        lines.append(f"## {category.replace('_', ' ').title()}")
        lines.append("")
        for _test_id, result in items:
            icon = "✓" if result["status"] == "executed" else "✗"
            lines.append(f"- [{icon}] **{result['name']}** — {result['status']}")
        lines.append("")

    executed = sum(1 for r in results.values() if r["status"] == "executed")
    total = len(results)
    lines.append(f"**Overall: {executed}/{total} checks executed successfully**")

    return "\n".join(lines)
