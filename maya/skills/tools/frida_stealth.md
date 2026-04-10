---
name: frida_stealth
description: Frida stealth attachment methodology - escalation tiers for anti-Frida protected apps
category: tools
version: "1.0"
last_updated: "2026-03-26"
applies_to: [dynamic, bypass, exploit]
---

# Frida Stealth Attachment Guide

## When to Use

Use this skill whenever an app crashes on Frida attachment, detects instrumentation, or you see anti-Frida behavior such as:
- App exits immediately after `frida_attach`
- Logcat shows "frida" string detection
- App checks `/proc/self/maps` or `/proc/self/task` for frida artifacts

## Anti-Frida Detection Methods

Before attempting stealth, identify what detection is in play:

1. **Process name scanning**: App enumerates processes looking for "frida-server"
2. **Port scanning**: App checks default port 27042
3. **Library scanning**: App scans `/proc/self/maps` for `frida-agent`
4. **D-Bus protocol detection**: App connects to 27042 and checks for D-Bus AUTH
5. **Inline hook detection**: App reads its own memory looking for trampolines

To fingerprint which methods are in use, decompile and grep:
```
terminal_execute(command="jadx -d /tmp/jadx_out <apk>")
terminal_execute(command="grep -rn 'frida\|xposed\|magisk\|substrate\|ptrace\|/proc/self/maps\|TracerPid' /tmp/jadx_out/")
terminal_execute(command="strings /tmp/decompiled/lib/arm64-v8a/*.so | grep -i frida")
```

## Escalation Tiers - Try in Order

### Tier 1: Standard Attachment
```
frida_attach(package_name="com.target.app")
```
Try this first. If the app doesn't crash, no stealth needed.

### Tier 2: Renamed Server + Non-Standard Port
```
device_shell("mv /data/local/tmp/frida-server /data/local/tmp/hluda-server-16.5.2")
device_shell("/data/local/tmp/hluda-server-16.5.2 --listen 0.0.0.0:9942 -D &")
```
Then attach using the non-standard host/port:
```
terminal_execute(command="frida -H <device-ip>:9942 -n com.target.app -l <script>")
```
This defeats process name scanning and default port checks.

### Tier 3: ZygiskFrida (Magisk Module)
Injects Frida gadget via Zygisk - no frida-server process at all.
```
1. device_push_file(local="zygisk-frida.zip", remote="/sdcard/")
2. device_shell("su -c magisk --install-module /sdcard/zygisk-frida.zip")
3. device_shell("su -c reboot")
4. After reboot:
   device_shell("su -c 'echo com.target.app > /data/local/tmp/re.zyg.fri/target_packages'")
5. Re-launch the target app - Frida gadget is now injected via Zygisk
```

### Tier 4: Gadget Embedding
Embed frida-gadget.so directly into the APK:
```
1. apk_decompile(apk_path="target.apk")
2. Copy frida-gadget.so to lib/{arch}/ in decompiled APK
3. Patch smali to load gadget early
4. apk_rebuild and resign
5. Install modified APK
```
Use `terminal_execute` with apktool/apksigner for the rebuild and signing steps.

### Tier 5: LD_PRELOAD (Root Required)
Last resort - forces library loading at process start:
```
device_shell("su -c 'echo /data/local/tmp/frida-gadget.so > /data/local/tmp/ld_preload'")
```
This is the most invasive but defeats all detection methods.

## Interpreting Results

- If Tier 1 works: app has no anti-Frida -> proceed normally
- If only Tier 2+ works: app specifically looks for Frida artifacts -> note in findings
- If Tier 3 needed: app has advanced detection - likely protected by DexGuard, iXGuard, or similar
- If nothing works: consider non-Frida alternatives (Xposed, manual binary patching)

## Key Decision

**Always try standard attachment first.** Only escalate when you observe detection. Each tier adds complexity and risk of side effects.
