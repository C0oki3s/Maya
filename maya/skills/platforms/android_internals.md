---
name: android_internals
description: Android platform internals, SELinux, Binder, providers, and app sandbox guidance
category: platforms
version: "1.0"
last_updated: "2026-03-26"
applies_to: [static, dynamic, exploit]
platform: [android]
---

# Android Internals Skill

## App Sandbox Model

Each app runs in its own Linux user ID. Data stored under `/data/data/<package>/` is isolated.

### Key Filesystem Paths

| Path | Contains | Security Risk |
|------|----------|---------------|
| `/data/data/<pkg>/shared_prefs/` | SharedPreferences XML files | Secrets stored in plaintext |
| `/data/data/<pkg>/databases/` | SQLite databases | Credentials, tokens, PII |
| `/data/data/<pkg>/files/` | App-created files | Logs with sensitive data |
| `/data/data/<pkg>/cache/` | Cached data | Response data, images |
| `/sdcard/Android/data/<pkg>/` | External storage | World-readable on older Android |
| `/data/local/tmp/` | Temp files, frida-server | Used for tool deployment |

## Exported Components

### Activities
- Check `AndroidManifest.xml` for `android:exported="true"` or intent-filters (auto-exported pre-Android 12)
- Test: `device_shell("am start -n <pkg>/<activity>")`
- Risk: Unauthorized access to internal screens

### Content Providers
- Query exported providers: `device_shell("content query --uri content://<authority>/")`
- Check `android:grantUriPermissions` and path-permission restrictions
- Risk: Data leakage, SQL injection via content URIs

### Broadcast Receivers
- Send crafted broadcasts: `device_shell("am broadcast -a <action> --es key value")`
- Risk: Triggering privileged actions without authorization

### Services
- Bind to exported services to test for unauthorized access
- Check for `android:permission` attributes

## SELinux

- Check mode: `device_shell("getenforce")` -> "Enforcing" or "Permissive"
- Enforcing mode blocks many Frida operations; set permissive for testing:
  `device_shell("setenforce 0")`
- Custom SELinux policies may block specific operations even in permissive

## Permissions Model

- Android 6+: Runtime permissions requested at use time
- `adb shell dumpsys package <pkg> | grep "permission"` - list granted permissions
- Dangerous permissions: CAMERA, LOCATION, CONTACTS, SMS, PHONE, STORAGE
- Check for over-privileged apps requesting more than needed

## Backup & Debug Flags

- `android:allowBackup="true"` -> `adb backup` can extract app data
- `android:debuggable="true"` -> attach debugger, JDWP access
- Both are HIGH findings in production apps

## Binder & IPC

- Android IPC uses Binder kernel driver
- Intent extras can carry sensitive data between components
- PendingIntents can be hijacked if mutable and exported
- Check for implicit intents that could be intercepted by malicious apps