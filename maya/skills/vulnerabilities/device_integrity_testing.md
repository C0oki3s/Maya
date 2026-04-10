---
name: device_integrity_testing
description: Device integrity, secure boot, emulator detection, root detection, and RASP assessment
category: vulnerabilities
version: "1.0"
last_updated: "2026-03-26"
requires: [frida_operations, frida_scripts, bypass_techniques]
applies_to: [dynamic, bypass]
platform: [android]
---

# Device Integrity Testing Skill

Comprehensive assessment of whether the app enforces device trustworthiness - secure boot, emulator detection, root detection, and RASP protections.

## Test Cases Covered

| # | Test Case | Script / Tool |
|---|-----------|---------------|
| 1 | Verify the app runs only on trusted devices with secure boot enabled | `secure_boot_check.js` + `device_shell` |
| 2 | Ensure the app detects and prevents execution in a virtualization environment | `emulator_detection.js` |
| 3 | Ensure the app enforces non-rooted/non-jailbroken device usage | `root_detection_universal.js` |
| 4 | Check for code obfuscation, RASP, and anti-debugging techniques | `rasp_detection.js` + `debug_detection.js` |

## Workflow

### Phase 1: Device Environment Assessment

1. **Check device trust properties** (without any bypass active):
```
device_shell("getprop ro.boot.verifiedbootstate")
device_shell("getprop ro.boot.flash.locked")
device_shell("getprop ro.boot.secureboot")
device_shell("getprop ro.debuggable")
device_shell("getprop ro.secure")
device_shell("getprop ro.build.type")
device_shell("getprop ro.build.tags")
```

2. **Run secure boot check script** to assess what the app can see:
```
file_read("~/.maya/frida-scripts/bypass/secure_boot_check.js")
frida_run_script(package_name="com.target", script=<content>)
```

### Phase 2: Root Detection Testing

1. **Test if app detects root** - launch app normally on rooted device and observe behavior:
   - Does the app refuse to start?
   - Does it show a warning?
   - Does it restrict features?

2. **Attempt root detection bypass**:
```
file_read("~/.maya/frida-scripts/bypass/root_detection_universal.js")
frida_run_script(package_name="com.target", script=<content>)
```

3. **Verify bypass effectiveness** - if app runs normally after bypass, root detection is bypassable.

### Phase 3: Emulator Detection Testing

1. **Launch app on emulator** - observe if app detects the environment.

2. **Attempt emulator detection bypass**:
```
file_read("~/.maya/frida-scripts/bypass/emulator_detection.js")
frida_run_script(package_name="com.target", script=<content>)
```

3. **Verify bypass** - if app runs on emulator after bypass, emulator detection is weak.

### Phase 4: RASP & Anti-Debugging Assessment

1. **Enumerate RASP libraries and protection level**:
```
file_read("~/.maya/frida-scripts/enumerate/rasp_detection.js")
frida_run_script(package_name="com.target", script=<content>)
```

2. **Test anti-debug protections**:
```
file_read("~/.maya/frida-scripts/bypass/debug_detection.js")
frida_run_script(package_name="com.target", script=<content>)
```

3. **Correlate with static analysis** - search decompiled code:
```
terminal_execute("grep -rn 'isDebuggerConnected\|ptrace\|TracerPid\|PTRACE_TRACEME' /tmp/jadx_out/")
terminal_execute("grep -rn 'ProGuard\|DexGuard\|obfuscat\|RASP\|tamper' /tmp/jadx_out/")
```

## Severity Guidance

| Finding | Severity | Condition |
|---------|----------|-----------|
| No secure boot enforcement | Medium | App runs on devices with unlocked bootloader without warning |
| Root detection bypassed | High | Single Frida script bypasses root detection completely |
| No root detection at all | High | App runs on rooted device with no checks |
| Emulator detection bypassed | Medium | App can be fully operated in emulator |
| No RASP protection | Medium | No commercial RASP library detected, no anti-debug |
| Anti-debug easily bypassed | Medium | Standard hooks defeat all debug detection |
| Strong RASP with layered controls | Informational | Note as a resilience positive |

## Remediation Guidance

- Implement hardware-backed device attestation (SafetyNet/Play Integrity API).
- Use server-side verification of device integrity tokens.
- Layer root detection: file checks + property checks + native checks + library detection.
- Use RASP solutions with anti-hooking (Frida detection, Xposed detection).
- Enforce verified boot state checks before processing sensitive data.
- Implement response strategies beyond just blocking - alert server, wipe local data.
