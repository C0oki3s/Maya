---
name: flutter_analysis
description: Flutter-specific reverse engineering and network instrumentation workflow
category: frameworks
version: "1.2"
last_updated: "2026-03-27"
requires: [reflutter_operations, frida_operations]
applies_to: [dynamic, static, flutter]
platform: [android, ios]
---

# Flutter Analysis Skill

Use this skill when the target embeds Flutter or Dart AOT artifacts and standard Java-layer hooks are insufficient.

## Discovery Workflow

1. Use `reflutter_analyze` to confirm Flutter packaging and surface runtime patch opportunities.
2. Use `reflutter_extract_dart_symbols` to recover meaningful Dart symbols when available.
3. Use `flutter_frida_hooks` or `frida_run_script` when traffic or crypto occurs below the Java layer.
4. Use `reflutter_patch_and_install` to patch, sign, set proxy, and install in one step.
5. Correlate Flutter findings with `caido_search_traffic` and `report_vulnerability` outputs.

## reFlutter Patch + Sign + Install Pipeline

When Flutter uses BoringSSL (bypasses Java-layer SSL hooks), use the full reFlutter pipeline:

### One-Step (Recommended)
```
reflutter_patch_and_install(apk_path="/tmp/target.apk", proxy_host="127.0.0.1", proxy_port="8083")
```
This will:
1. Patch the APK with reFlutter (patches BoringSSL for traffic interception)
2. Sign with `uber-apk-signer-1.3.0.jar`
3. Set system-wide proxy to `127.0.0.1:8083`
4. Install the signed patched APK on device

### Manual Steps
```
# 1. Analyze & patch
reflutter_analyze(apk_path="/tmp/target.apk")

# 2. Sign the patched APK
sign_apk(apk_path="/tmp/release.RE.apk")

# 3. Switch proxy to port 8083 system-wide
device_set_proxy(host="127.0.0.1", port="8083")

# 4. Install on device
device_install_app(app_path="/tmp/release.RE.apk")

# 5. After testing - clear proxy
device_clear_proxy()
```

### Why Port 8083?

reFlutter patches the Flutter engine to route traffic through a specific proxy. Using port 8083 (instead of the default 8080) avoids conflict with Caido/Burp on 8080 and matches reFlutter's typical configuration.

## Tool Quick Reference

- `reflutter_analyze`: detects Flutter and prepares framework-specific analysis.
- `reflutter_patch_and_install`: Full pipeline - patch, sign, set proxy 8083, install.
- `reflutter_extract_dart_symbols`: recovers Dart names and structural clues.
- `sign_apk`: Signs APK with uber-apk-signer (required after any APK modification).
- `device_set_proxy`: Sets system-wide HTTP proxy on device.
- `device_clear_proxy`: Removes system-wide proxy after testing.
- `flutter_frida_hooks`: installs Flutter or native-layer runtime hooks.
- `frida_run_script`: supplies custom native or hybrid instrumentation.

## High-Value Checks

- TLS enforcement implemented below the Java networking stack.
- Sensitive logic inside Dart isolates with weak client-side trust assumptions.
- Hardcoded environment URLs or API secrets in assets or snapshots.
- Release builds exposing debug-only channels or verbose logging.

## Remediation

- Keep secrets and trust decisions server-side.
- Remove debug artifacts from production builds.
- Use modern transport protections and test them at the native layer.