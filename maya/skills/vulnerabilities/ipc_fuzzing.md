---
name: ipc_fuzzing
description: IPC attack surface testing - deeplinks, intents, content providers, broadcast receivers
category: vulnerabilities
version: "1.0"
last_updated: "2026-03-26"
requires: [adb_operations, frida_operations]
applies_to: [dynamic, exploit]
---

# IPC & Deeplink Fuzzing Methodology

## Step 1: Enumerate Attack Surface

### Deeplinks / URL Schemes
```
terminal_execute("aapt dump xmltree <apk_path> AndroidManifest.xml | grep -B5 -A5 'scheme'")
```
Or from decompiled manifest:
```
terminal_execute("grep -A10 'intent-filter' /tmp/decompiled/AndroidManifest.xml | grep -E 'scheme|host|path'")
```

### Exported Components
```
device_shell("dumpsys package <package> | grep -A2 'exported=true'")
terminal_execute("grep 'exported=\"true\"' /tmp/decompiled/AndroidManifest.xml")
```

### Content Providers
```
device_shell("content query --uri content://<package>.provider/ --projection '*'")
terminal_execute("grep 'android:authorities' /tmp/decompiled/AndroidManifest.xml")
```

## Step 2: Deeplink Fuzzing

For each discovered scheme (e.g. `myapp://`), test these payloads:

Use payloads from the wordlist:
```
file_read("~/.maya/wordlists/deeplink-payloads.txt")
```

For each payload, launch via ADB:
```
device_shell("am start -a android.intent.action.VIEW -d '<scheme>://<payload>' <package>")
```

### Key Payloads to Test
- Path traversal: `myapp://../../etc/passwd`
- JavaScript injection: `myapp://page?url=javascript:alert(1)`
- Open redirect: `myapp://redirect?to=https://evil.com`
- SQL injection: `myapp://search?q=' OR 1=1 --`
- Long input: `myapp://path/` + "A" * 500
- File access: `myapp://load?file=file:///data/data/<pkg>/databases/db`

### What to Monitor
After each payload:
- Check logcat for crashes: `device_shell("logcat -d -t 10 | grep -i 'fatal\|crash\|exception'")`
- Check if the app is still running: `device_shell("pidof <package>")`
- Check for data leakage in traffic: `caido_search_traffic(query="req.host.cont:\"evil.com\"")`

## Step 3: Intent Fuzzing

### Broadcast to exported receivers:
```
device_shell("am broadcast -a <action> -n <package>/<receiver_class> --es key 'payload'")
```

### Start exported activities with extras:
```
device_shell("am start -n <package>/<activity_class> --es url 'javascript:alert(1)' --es redirect 'https://evil.com'")
```

### Test PendingIntent hijacking:
If an exported component creates a PendingIntent with an empty/implicit base Intent, another app could fill in the extras and redirect the action. Look for:
```
terminal_execute("grep -rn 'PendingIntent\|getActivity\|getBroadcast\|getService' /tmp/jadx_out/ | grep -v 'FLAG_IMMUTABLE'")
```
Missing FLAG_IMMUTABLE on PendingIntent = hijackable.

## Step 4: Content Provider Exploitation

```
device_shell("content query --uri content://<authority>/ --projection '*'")
device_shell("content read --uri content://<authority>/../../etc/passwd")
```

Test for path traversal in content providers:
```
device_shell("content query --uri content://<authority>/..%2F..%2Fetc%2Fpasswd")
```

## Step 5: Activity Task Hijacking

Check for vulnerable task configurations:
```
terminal_execute("grep -E 'taskAffinity|launchMode|allowTaskReparenting' /tmp/decompiled/AndroidManifest.xml")
```

If `taskAffinity` is set to a different package's affinity + `allowTaskReparenting=true`, the activity can be hijacked by a malicious app.

## Reporting

| Finding | Severity |
|---------|----------|
| Deeplink open redirect | MEDIUM |
| Deeplink JavaScript injection in WebView | HIGH |
| Content provider path traversal | HIGH |
| PendingIntent hijack (missing FLAG_IMMUTABLE) | MEDIUM |
| Activity task hijacking | MEDIUM |
| Deeplink causing crash (DoS) | LOW |
