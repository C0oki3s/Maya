---
name: ios_testing
description: iOS-specific testing methodology - decryption, ATS analysis, runtime instrumentation, binary checks
category: platforms
version: "1.0"
last_updated: "2026-03-26"
requires: [frida_operations]
applies_to: [ios, dynamic, static]
---

# iOS Testing Methodology

## Device Access

All iOS device commands use SSH to a jailbroken device:
```
terminal_execute("ssh root@<device_ip> '<command>'")
```
Or via `device_shell` if configured for iOS.

## Step 1: IPA Decryption

Apps from App Store are encrypted. Must decrypt first:

### Method 1: Clutch (preferred)
```
device_shell("clutch -d <bundle_id>")
```

### Method 2: flexdecrypt
```
device_shell("flexdecrypt /var/containers/Bundle/Application/<UUID>/<app>.app/<binary>")
```

### Method 3: bfdecrypt (Frida-based)
```
file_read("~/.maya/frida-scripts/ios/bfdecrypt.js")
frida_run_script(package_name="<bundle_id>", script_code=<content>)
```

## Step 2: App Transport Security (ATS) Analysis

```
terminal_execute("plutil -convert json -o /tmp/info.json /tmp/decrypted.app/Info.plist")
file_read("/tmp/info.json")
```

Look at `NSAppTransportSecurity` key:
- `NSAllowsArbitraryLoads: true` -> **HIGH**: All HTTP allowed
- `NSExceptionDomains` with `NSExceptionAllowsInsecureHTTPLoads` -> per-domain bypass
- `NSExceptionMinimumTLSVersion: "TLSv1.0"` or `"TLSv1.1"` -> **MEDIUM**: Weak TLS

## Step 3: Entitlement Analysis

```
terminal_execute("codesign -d --entitlements :- /tmp/decrypted.app")
```

Dangerous entitlements:
| Entitlement | Risk |
|-------------|------|
| `get-task-allow = true` | CRITICAL - debuggable in production |
| `com.apple.developer.associated-domains` | Deeplink attack surface |
| `keychain-access-groups` | Shared keychain - check what's shared |
| `com.apple.security.application-groups` | Shared container - data leakage risk |
| `com.apple.developer.networking.wifi-info` | WiFi SSID access - location tracking |

## Step 4: Binary Analysis

```
terminal_execute("otool -l /tmp/decrypted.app/<binary> | grep -A2 'LC_ENCRYPTION_INFO'")
terminal_execute("otool -L /tmp/decrypted.app/<binary>")  - linked frameworks
terminal_execute("class-dump -H /tmp/decrypted.app/<binary> -o /tmp/headers/")
terminal_execute("strings /tmp/decrypted.app/<binary> | grep -i 'http\|api\|key\|secret\|token' | head -50")
```

Check security features:
```
terminal_execute("otool -l /tmp/decrypted.app/<binary> | grep -E 'PIE|stackguard|objc_release'")
```

## Step 5: Runtime Instrumentation (Frida on iOS)

### Pasteboard Monitoring
```
frida_run_script(package_name="<bundle_id>", script_code="
ObjC.perform(function() {
  var pb = ObjC.classes.UIPasteboard.generalPasteboard();
  Interceptor.attach(ObjC.classes.UIPasteboard['- setString:'].implementation, {
    onEnter: function(args) { send({type: 'pasteboard_write', value: ObjC.Object(args[2]).toString()}); }
  });
});
")
```

### NSURLSession Hook (capture requests)
```
file_read("~/.maya/frida-scripts/ios/nsurlsession_hook.js")
frida_run_script(package_name="<bundle_id>", script_code=<content>)
```

### Runtime Class Dump
```
frida_run_script(package_name="<bundle_id>", script_code="
ObjC.perform(function() {
  var classes = ObjC.classes;
  for (var name in classes) {
    if (name.indexOf('<AppPrefix>') === 0) send({type: 'class', name: name});
  }
});
")
```

### Data Protection Class Check
```
file_read("~/.maya/frida-scripts/ios/data_protection.js")
frida_run_script(package_name="<bundle_id>", script_code=<content>)
```
Monitors NSFileManager and NSData file operations to verify data protection levels.

## Step 6: URL Scheme Fuzzing

```
terminal_execute("plutil -extract CFBundleURLTypes json -o - /tmp/decrypted.app/Info.plist")
```

For each discovered scheme, test payloads:
```
device_shell("uiopen '<scheme>://test'")
device_shell("uiopen '<scheme>://../../etc/passwd'")
device_shell("uiopen '<scheme>://javascript:alert(1)'")
device_shell("uiopen '<scheme>://" + "A" * 500 + "'")
```

Monitor for crashes: `device_shell("log show --predicate 'process == \"<app>\"' --last 30s")`

## iOS vs Android Comparison

| Area | Android Tool | iOS Equivalent |
|------|-------------|----------------|
| Decompile | `apktool d` / `jadx` | `class-dump` / `otool` |
| Shell | `adb shell` | `ssh root@device` |
| Install | `adb install` | `ideviceinstaller` |
| Launch URL | `am start -a VIEW -d` | `uiopen` |
| Frida | `frida -U -f <pkg>` | `frida -U -f <bundle_id>` |
| File system | `/data/data/<pkg>` | `/var/mobile/Containers/Data/Application/<UUID>` |
| Logs | `logcat` | `log show` / `oslog` |
