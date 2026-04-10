from __future__ import annotations

import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

from .registry import register_tool


@register_tool(sandbox_execution=True)
def apktool_decompile(apk_path: str, output_dir: str) -> dict:
    """Decompile an APK using apktool."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cmd = ["apktool", "d", apk_path, "-f", "-o", str(out)]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=180)
    return {
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "exit_code": proc.returncode,
        "output_dir": str(out),
    }


@register_tool(sandbox_execution=True)
def jadx_decompile(apk_path: str, output_dir: str) -> dict:
    """Decompile an APK using JADX."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cmd = ["jadx", "-d", str(out), apk_path]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=180)
    return {
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "exit_code": proc.returncode,
        "output_dir": str(out),
    }


@register_tool(sandbox_execution=True)
def analyze_manifest(manifest_path: str) -> dict:
    """Parse AndroidManifest.xml and summarize package, permissions, and exported components."""
    path = Path(manifest_path)
    if not path.exists():
        return {"error": f"manifest not found: {manifest_path}"}

    root = ET.fromstring(path.read_text(encoding="utf-8"))  # noqa: S314
    ns = {"android": "http://schemas.android.com/apk/res/android"}
    package_name = root.attrib.get("package", "")
    permissions = [
        element.attrib.get("{http://schemas.android.com/apk/res/android}name", "")
        for element in root.findall("uses-permission")
    ]

    components: dict[str, list[dict[str, str]]] = {"activity": [], "service": [], "receiver": [], "provider": []}
    application = root.find("application")
    if application is not None:
        for tag_name, key in [
            ("activity", "activity"),
            ("service", "service"),
            ("receiver", "receiver"),
            ("provider", "provider"),
        ]:
            for element in application.findall(tag_name):
                components[key].append(
                    {
                        "name": element.attrib.get("{http://schemas.android.com/apk/res/android}name", ""),
                        "exported": element.attrib.get("{http://schemas.android.com/apk/res/android}exported", ""),
                        "permission": element.attrib.get("{http://schemas.android.com/apk/res/android}permission", ""),
                    }
                )

    return {
        "package": package_name,
        "permissions": sorted(p for p in permissions if p),
        "components": components,
        "xmlns": ns,
    }


@register_tool(sandbox_execution=True)
def search_decompiled_code(path: str, pattern: str) -> dict:
    """Search decompiled code with ripgrep and return matches."""
    cmd = ["rg", "-n", pattern, path]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=90)
    return {
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "exit_code": proc.returncode,
    }


@register_tool(sandbox_execution=True)
def ios_class_dump(binary_path: str, output_dir: str) -> dict:
    """Extract Objective-C headers from an iOS binary using class-dump."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    cmd = ["class-dump", "-H", binary_path, "-o", str(out)]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=180)
    return {
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "exit_code": proc.returncode,
        "output_dir": str(out),
    }


@register_tool(sandbox_execution=True)
def extract_strings(binary_path: str, min_length: str = "4") -> dict:
    """Extract printable strings from a binary or file."""
    if not re.fullmatch(r"\d+", min_length):
        return {"error": "min_length must be numeric"}
    cmd = ["strings", "-n", min_length, binary_path]
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=120)
    return {
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "exit_code": proc.returncode,
    }


# ---------- APK signer path ----------
_SIGNER_JAR = Path(__file__).resolve().parent.parent.parent / "assets" / "signer" / "uber-apk-signer-1.3.0.jar"


@register_tool(sandbox_execution=True)
def apktool_rebuild(decompiled_dir: str, output_apk: str = "", timeout: str = "180") -> dict:
    """Rebuild a tampered APK from an apktool-decompiled directory."""
    src = Path(decompiled_dir)
    if not src.is_dir():
        return {"error": f"Decompiled directory not found: {decompiled_dir}"}

    out_path = output_apk or str(src.parent / f"{src.name}-rebuilt.apk")
    cmd = ["apktool", "b", str(src), "-o", out_path]
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=int(timeout))
        return {
            "status": "ok" if proc.returncode == 0 else "build_failed",
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "output_apk": out_path,
        }
    except Exception as exc:
        return {"error": str(exc)}


@register_tool(sandbox_execution=True)
def sign_apk(apk_path: str, timeout: str = "120") -> dict:
    """Sign an APK using uber-apk-signer. Required after any APK modification."""
    apk = Path(apk_path)
    if not apk.exists():
        return {"error": f"APK not found: {apk_path}"}
    if not _SIGNER_JAR.exists():
        return {"error": f"Signer JAR not found: {_SIGNER_JAR}"}

    cmd = ["java", "-jar", str(_SIGNER_JAR), "--apks", str(apk), "--overwrite"]
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=int(timeout))
        return {
            "status": "ok" if proc.returncode == 0 else "sign_failed",
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "signed_apk": str(apk),
        }
    except Exception as exc:
        return {"error": str(exc)}


@register_tool(sandbox_execution=True)
def tamper_and_install(decompiled_dir: str, package_name: str = "", timeout: str = "300") -> dict:
    """Rebuild, sign, and install a tampered APK in one step.

    Full code-tampering pipeline: apktool rebuild -> uber-apk-signer -> adb install.
    Use after modifying files in an apktool-decompiled directory."""
    # Step 1: Rebuild
    rebuild = apktool_rebuild(decompiled_dir, timeout=str(min(int(timeout), 180)))
    if "error" in rebuild or rebuild.get("exit_code") != 0:
        return {
            "error": f"Rebuild failed: {rebuild.get('error') or rebuild.get('stderr', '')}",
            "step": "rebuild",
            "detail": rebuild,
        }

    apk_path = rebuild["output_apk"]

    # Step 2: Sign
    signed = sign_apk(apk_path, timeout="120")
    if "error" in signed or signed.get("exit_code") != 0:
        return {
            "error": f"Signing failed: {signed.get('error') or signed.get('stderr', '')}",
            "step": "sign",
            "detail": signed,
        }

    # Step 3: Install
    from .device_bridge import device_install_app

    installed = device_install_app(apk_path, timeout="120")
    if installed.get("exit_code") != 0:
        return {"error": f"Install failed: {installed.get('stderr', '')}", "step": "install", "detail": installed}

    return {
        "status": "ok",
        "apk_path": apk_path,
        "package_name": package_name,
        "rebuild": {"exit_code": rebuild["exit_code"]},
        "sign": {"exit_code": signed["exit_code"]},
        "install": {"exit_code": installed["exit_code"]},
    }
