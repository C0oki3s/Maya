---
name: static_analysis
description: Static analysis methodology - semgrep, dependency audit, binary checks, manifest analysis
category: tools
version: "1.0"
last_updated: "2026-03-26"
applies_to: [static, recon]
---

# Static Analysis Methodology

## Overview

Static analysis uses `terminal_execute` and `file_read` to run external tools and inspect results. No special tool wrappers needed.

## Step 1: Decompile

```
terminal_execute("apktool d <apk_path> -o /tmp/decompiled/")
terminal_execute("jadx -d /tmp/jadx_out/ <apk_path>")
```

## Step 2: Semgrep Mobile Rules

Run Semgrep with mobile-specific rulesets:
```
terminal_execute("semgrep --config=p/android --config=p/java --json -o /tmp/semgrep_results.json /tmp/jadx_out/")
```

For custom rules:
```
terminal_execute("semgrep --config=~/.maya/semgrep-rules/ --json -o /tmp/semgrep_custom.json /tmp/jadx_out/")
```

Read results:
```
file_read("/tmp/semgrep_results.json")
```

Common rulesets: `p/android`, `p/java`, `p/kotlin`, `p/owasp-mobile-top-10`, `p/secrets`

## Step 3: Dependency Audit

### Android (Gradle)
```
terminal_execute("cat /tmp/decompiled/build.gradle")
terminal_execute("osv-scanner --lockfile=/tmp/decompiled/gradle.lockfile --json")
```

### iOS (CocoaPods)
```
terminal_execute("cat Podfile.lock")
terminal_execute("osv-scanner --lockfile=Podfile.lock --json")
```

If osv-scanner not available:
```
terminal_execute("pip install pip-audit && pip-audit")  - for Python dependencies
```

## Step 4: Manifest Deep Audit

Check these security anti-patterns in AndroidManifest.xml:
```
file_read("/tmp/decompiled/AndroidManifest.xml")
```

### What to Look For
| Pattern | Command | Severity |
|---------|---------|----------|
| Debuggable | `grep 'debuggable="true"'` | HIGH |
| Backup allowed | `grep 'allowBackup="true"'` | MEDIUM |
| Cleartext traffic | `grep 'usesCleartextTraffic="true"'` | HIGH |
| Exported components without permission | `grep 'exported="true"'`, then check for `android:permission` | MEDIUM-HIGH |
| Custom permissions with wrong protectionLevel | `grep 'protectionLevel'` - should be "signature" not "normal" | HIGH |
| Task affinity (hijack risk) | `grep 'taskAffinity'` | MEDIUM |
| Backup agent | `grep 'backupAgent'` | LOW |

## Step 5: Binary Analysis

```
terminal_execute("checksec --file=/tmp/decompiled/lib/arm64-v8a/*.so")
```

If checksec not available, check manually:
```
terminal_execute("readelf -h /tmp/decompiled/lib/arm64-v8a/*.so | grep -E 'Type|Entry'")
terminal_execute("readelf -d /tmp/decompiled/lib/arm64-v8a/*.so | grep -E 'RELRO|BIND_NOW|NEEDED'")
```

Look for dangerous imports:
```
terminal_execute("nm -D /tmp/decompiled/lib/arm64-v8a/*.so | grep -E 'system|exec|popen|dlopen|ptrace|mprotect'")
```

## Step 6: Secret/Key Scanning

```
terminal_execute("grep -rn 'API_KEY\|SECRET\|PASSWORD\|PRIVATE_KEY\|Bearer\|token' /tmp/jadx_out/ --include='*.java' --include='*.kt'")
terminal_execute("grep -rn 'https://\|http://' /tmp/jadx_out/ --include='*.java' | head -50")
```

For ProGuard/R8 mapped code:
```
terminal_execute("retrace /tmp/decompiled/mapping.txt /tmp/stacktrace.txt")
```

## Step 7: iOS Entitlement Audit

```
terminal_execute("codesign -d --entitlements :- <app_path>")
```

Dangerous entitlements to flag:
- `com.apple.developer.associated-domains` - deeplink attack surface
- `keychain-access-groups` - shared keychain risk
- `com.apple.security.application-groups` - shared container risk
- `get-task-allow` - debuggable in production = CRITICAL
- `com.apple.developer.team-identifier` - check if still dev team
