---
name: bypass_techniques
description: Runtime protection bypass methodology - SafetyNet, root, emulator, debug, anti-tamper
category: vulnerabilities
version: "1.0"
last_updated: "2026-03-26"
requires: [frida_operations, frida_stealth]
applies_to: [dynamic, bypass]
---

# Runtime Protection Bypass Methodology

## Purpose

Many apps implement runtime protections. This skill teaches HOW to bypass each using basic tools.

## Step 1: Detect What Protections Exist

```
terminal_execute("grep -rn 'SafetyNet\|PlayIntegrity\|RootBeer\|isRooted\|isEmulator\|isDebugger\|tamper\|integrity' /tmp/jadx_out/")
```

Also check native code:
```
terminal_execute("strings /tmp/decompiled/lib/arm64-v8a/*.so | grep -i 'root\|frida\|magisk\|debug\|emulator'")
```

## SafetyNet / Play Integrity Bypass

### Method 1: Magisk Props (if Magisk is available)
```
device_shell("su -c resetprop ro.debuggable 0")
device_shell("su -c resetprop ro.secure 1")
device_shell("su -c resetprop ro.build.type user")
device_shell("su -c resetprop ro.build.tags release-keys")
```

### Method 2: Frida Hook
Load the bypass script from assets:
```
file_read("~/.maya/frida-scripts/bypass/safetynet_bypass.js")
frida_run_script(package_name="com.target", script_code=<content>)
```

The safetynet_bypass.js script hooks `SafetyNet.getClient` and `onSuccess` to return a valid attestation.

## Root Detection Bypass

### Method 1: Load universal root bypass
```
file_read("~/.maya/frida-scripts/bypass/root_detection_universal.js")
frida_run_script(package_name="com.target", script_code=<content>)
```

This script:
- Hooks `File.exists()` to hide su, Magisk, Superuser paths
- Hooks `Runtime.exec()` to block which/su commands
- Spoofs `Build.TAGS` to remove "test-keys"
- Intercepts RootBeer-specific checks if that library is present

### Method 2: MagiskHide / Zygisk DenyList
```
device_shell("su -c magisk --denylist add <package_name>")
```

## Emulator Detection Bypass

Load the emulator detection bypass script:
```
file_read("~/.maya/frida-scripts/bypass/emulator_detection.js")
frida_run_script(package_name="com.target", script_code=<content>)
```

This script spoofs:
- `Build.FINGERPRINT`, `Build.MODEL`, `Build.MANUFACTURER` -> real device values
- `TelephonyManager.getDeviceId()` -> non-emulator IMEI
- Sensor availability checks -> reports real sensors present

## Debug Detection Bypass

### Method 1: Frida-based
```
file_read("~/.maya/frida-scripts/bypass/debug_detection.js")
frida_run_script(package_name="com.target", script_code=<content>)
```

This hooks:
- `android.os.Debug.isDebuggerConnected()` -> returns false
- `ptrace` native call -> returns 0
- `/proc/self/status` reads -> hides TracerPid
- `ApplicationInfo.flags` -> clears FLAG_DEBUGGABLE

### Method 2: Direct process manipulation
```
device_shell("su -c 'echo 0 > /proc/<pid>/status'")  - not always effective
```

## Anti-Tamper / Integrity Check Bypass

These are app-specific. General approach:

1. Find the integrity check class:
   ```
   terminal_execute("grep -rn 'PackageManager\|signatures\|checksum\|MessageDigest\|hashCode' /tmp/jadx_out/ | grep -i 'verify\|check\|tamper\|integrity'")
   ```

2. Load generic integrity bypass:
   ```
   file_read("~/.maya/frida-scripts/bypass/integrity_check.js")
   frida_run_script(package_name="com.target", script_code=<content>)
   ```

3. If generic doesn't work, write targeted hook:
   ```
   frida_run_script(package_name="com.target", script_code="Java.perform(function() { var cls = Java.use('<detected_class>'); cls.<check_method>.implementation = function() { return true; }; });")
   ```

## Decision Flow

```
App crashes/restricts features?
|-- Check what protections exist (grep decompiled source)
|-- Root detection? -> Try Magisk DenyList first, then Frida bypass
|-- SafetyNet/Play Integrity? -> Magisk props + Frida hook
|-- Emulator detection? -> Frida emulator spoof
|-- Debug detection? -> Frida debug bypass
|-- Anti-tamper? -> Identify check class, hook it
+-- Multiple protections? -> Compose a single script with all bypasses:
    file_read each needed script, concatenate, frida_run_script once
```
