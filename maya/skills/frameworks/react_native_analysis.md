---
name: react_native_analysis
description: React Native bundle, bridge, and native-module assessment workflow
category: frameworks
version: "1.0"
last_updated: "2026-03-26"
applies_to: [static, dynamic]
platform: [android, ios]
---

# React Native Analysis Skill

## Detection

Detect React Native apps by looking for these artifacts:
- `libreactnativejni.so` in `lib/` (Android)
- `assets/index.android.bundle` or `assets/index.ios.bundle`
- `libhermes.so` (Hermes engine) or `libjsc.so` (JavaScriptCore)
- `node_modules` references in decompiled code

## Step 1: Extract JavaScript Bundle

### Android
```
terminal_execute("unzip -o <apk_path> assets/index.android.bundle -d /tmp/rn/")
```

### Hermes Bytecode
If the bundle is Hermes compiled (binary, not readable JS):
```
terminal_execute("file /tmp/rn/assets/index.android.bundle")
```
If it shows "Hermes JavaScript bytecode", decompile:
```
terminal_execute("hermes-dec /tmp/rn/assets/index.android.bundle -o /tmp/rn/decompiled.js")
```

### Plain JS Bundle
If readable JS, search directly:
```
terminal_execute("grep -n 'api\|token\|secret\|password\|apiKey\|Authorization' /tmp/rn/assets/index.android.bundle | head -50")
```

## Step 2: Analyze Bridge Modules

Native bridge modules expose native functionality to JavaScript. Look for:
```
terminal_execute("grep -rn 'ReactMethod\|@ReactModule\|NativeModules' /tmp/jadx_out/ | head -30")
```

Security concerns:
- Bridge methods that execute shell commands
- Bridge methods that access keychain/keystore without validation
- Bridge methods that handle file I/O without path validation
- Custom bridge modules exposing internal APIs

## Step 3: Deep Link & Navigation

React Navigation routes are defined in JS. Search for:
```
terminal_execute("grep -n 'createStackNavigator\|createDrawerNavigator\|Linking.addEventListener\|deeplink\|scheme' /tmp/rn/assets/index.android.bundle | head -20")
```

## Step 4: Runtime Instrumentation

Hook the JS bridge to monitor all bridge calls:
```
frida_run_script(package_name="<pkg>", script_code="<bridge-monitor script>")
```

Monitor for sensitive data crossing the bridge (tokens, PII, credentials).

## Remediation

- Minimize sensitive logic in the JS layer
- Harden native bridge input validation
- Keep server-side authorization authoritative
- Use Hermes bytecode compilation to raise analysis difficulty
- Do not store secrets in JS bundle or AsyncStorage