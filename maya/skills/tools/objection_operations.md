---
name: objection_operations
description: Objection operational workflow and Frida interoperability guidance
category: tools
version: "2.0"
last_updated: "2026-03-26"
requires: [frida_operations]
applies_to: [dynamic]
platform: [android, ios]
---

# Objection Operations Guide

## Prerequisites

1. Objection is built on top of Frida - all Frida prerequisites apply (see `frida_operations`)
2. Install check: `terminal_execute(command="objection --version")`
3. Frida version must be compatible with Objection version
4. frida-server must be running on device before Objection can connect

## When to Use Objection vs Raw Frida

| Task | Use Objection | Use Raw Frida |
|------|--------------|---------------|
| Quick storage enumeration | Yes - built-in commands | Overkill |
| Keychain/keystore dump | Yes - `keychain dump` | Overkill |
| Component listing | Yes - `android hooking list activities` | Overkill |
| Disable SSL pinning | Either - `android sslpinning disable` | Use for fine-grained control |
| Custom method hooking | No - limited | Yes - full flexibility |
| Complex exploit validation | No - limited JS support | Yes - write custom scripts |
| Multi-hook compositions | No - single purpose | Yes - combine scripts |

## Common Operations

### Storage Enumeration (Android)
`
objection_run_command(command="android hooking list activities")
objection_run_command(command="android hooking list services")
objection_run_command(command="android hooking list receivers")
objection_run_command(command="android keystore list")
objection_run_command(command="env")
`

### Storage Enumeration (iOS)
`
objection_run_command(command="ios keychain dump")
objection_run_command(command="ios plist cat <path>")
objection_run_command(command="ios cookies get")
objection_run_command(command="ios nsurlcredentialstorage dump")
objection_run_command(command="env")
`

### Quick SSL Bypass
`
objection_run_command(command="android sslpinning disable")
`
Note: This is simpler but less comprehensive than the universal Frida script.

### File System Exploration
`
objection_run_command(command="ls /data/data/<package>/shared_prefs/")
objection_run_command(command="cat /data/data/<package>/shared_prefs/<file>.xml")
objection_run_command(command="sqlite connect /data/data/<package>/databases/<db>")
`

## Conflict Rule

Objection and raw Frida MUST NOT control the same process at the same time. They both use Frida under the hood, and concurrent sessions will crash.

**Workflow**: Finish all Objection recon first, then disconnect Objection, then start Frida hooks.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Unable to connect to Frida" | Check frida-server is running, check version match |
| "Application not found" | Use full package name: `com.example.app` |
| SSL bypass not working | Use raw Frida with universal bypass script for better coverage |
| Keychain dump empty | App may use custom keychain wrapper - use Frida to hook SecItemCopyMatching |