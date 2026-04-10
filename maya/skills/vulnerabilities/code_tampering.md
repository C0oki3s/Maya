---
name: code_tampering
description: Anti-tamper, anti-debug, and integrity-control testing
category: vulnerabilities
version: "1.1"
last_updated: "2026-03-26"
requires: [frida_operations, apktool_operations]
applies_to: [dynamic, static]
---

# Code Tampering Skill

Use this skill when evaluating whether the app can be modified, repackaged, debugged, or instrumented without detection.

## Workflow

### Phase 1: Static Analysis - Find Integrity Checks

1. Search decompiled code for anti-tamper, signature checks, and integrity verification:
```
terminal_execute("grep -rn 'PackageManager\|getPackageInfo\|signatures\|checkSignature\|MessageDigest\|integrity\|tamper' /tmp/jadx_out/")
terminal_execute("grep -rn 'isDebuggerConnected\|ptrace\|TracerPid\|PTRACE_TRACEME' /tmp/jadx_out/")
```

### Phase 2: Tamper the APK (APKTool + uber-apk-signer)

1. **Decompile** the target APK:
```
apktool_decompile(apk_path="/tmp/target.apk", output_dir="/tmp/tampered")
```

2. **Modify files** to test tamper detection - e.g. inject a log statement, change a string resource, or modify a smali file:
```
device_shell("echo '# tampered' >> /tmp/tampered/smali/com/target/MainActivity.smali")
```

3. **Rebuild, sign, and install** in one step:
```
tamper_and_install(decompiled_dir="/tmp/tampered", package_name="com.target")
```

Or step by step:
```
apktool_rebuild(decompiled_dir="/tmp/tampered")
sign_apk(apk_path="/tmp/tampered-rebuilt.apk")
device_install_app(app_path="/tmp/tampered-rebuilt.apk")
```

The signer is at `assets/signer/uber-apk-signer-1.3.0.jar` and is called automatically.

### Phase 3: Observe Tamper Detection Response

1. **Launch the tampered app** and observe:
   - Does it refuse to start? -> Tamper detection active
   - Does it show a warning? -> Detection present but permissive
   - Does it run normally? -> No effective tamper detection

2. **Use Frida to bypass detected checks**:
```
file_read("~/.maya/frida-scripts/bypass/integrity_check.js")
frida_run_script(package_name="com.target", script=<content>)
```

3. **Re-run sensitive flows** while instrumented to see whether controls actually block abuse.

## High-Value Checks

- Signature checks implemented only in client code.
- Anti-debug logic bypassed with trivial hook changes.
- Integrity failures logged but not enforced.
- App runs after repackaging with modified code.

## Tool Quick Reference

- `apktool_decompile`: Decompile APK to smali/resources.
- `apktool_rebuild`: Rebuild APK from modified decompiled directory.
- `sign_apk`: Sign APK with uber-apk-signer (required after rebuild).
- `tamper_and_install`: One-step rebuild -> sign -> install pipeline.
- `frida_run_script` + `integrity_check.js`: Bypass runtime integrity checks.

## Remediation

- Move trust decisions server-side where possible.
- Layer integrity controls and fail closed.
- Use hardware-backed attestation where appropriate.