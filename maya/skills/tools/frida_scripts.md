---
name: frida_scripts
description: Pre-built Frida script library - when and how to use each module
category: tools
version: "1.0"
last_updated: "2026-03-26"
applies_to: [dynamic, bypass, extract, exploit]
---

# Frida Script Library Guide

## Overview

Pre-built Frida scripts are stored as `.js` asset files in `~/.maya/frida-scripts/` (or `assets/frida-scripts/` in the project). To use a script:
1. `file_read` the script to get its contents
2. `frida_run_script(package_name="...", script=<contents>)` to execute it

## When to Compose vs Use Single Module

- **Single module**: Use for focused tasks - e.g., just bypass SSL pinning
- **Composed script**: Use `file_read` on each script, concatenate the JS code, then pass to `frida_run_script`. Common compositions:
  - `ssl_pinning_universal + root_detection_universal` - standard bypass combo
  - `ssl_pinning_flutter + root_detection_universal` - for Flutter apps
  - `crypto_keys + network_requests` - capture keys and traffic together
  - `sqlite_queries + shared_preferences` - full data access monitoring  - `secure_boot_check + root_detection_universal + emulator_detection` - full device integrity assessment
  - `crypto_keys + tls_version_check + data_containerization_check` - full encryption compliance audit
  - `rasp_detection + debug_detection + integrity_check` - complete code protection assessment
## Module Categories

### Bypass Modules
| Module | When to Use |
|--------|------------|
| `ssl_pinning_universal` | Default first choice for SSL bypass. Covers OkHttp, TrustManager, WebView |
| `ssl_pinning_flutter` | Only for Flutter/Dart apps (detected via `framework_detect`) |
| `root_detection_universal` | When app detects root/jailbreak and exits or restricts features |
| `emulator_detection` | When app detects emulator environment |
| `debug_detection` | When app has anti-debug protection |
| `integrity_check` | When app verifies its own signature/checksum |
| `secure_boot_check` | To verify device trust properties, verified boot state, and attestation APIs |

### Extract Modules
| Module | When to Use |
|--------|------------|
| `crypto_keys` | To capture encryption keys at runtime (AES, RSA, etc.) |
| `shared_preferences` | To monitor preference reads/writes (tokens, config) |
| `sqlite_queries` | To intercept all SQLite operations |
| `network_requests` | To capture HTTP requests before encryption |
| `jwt_tokens` | To intercept JWT creation/validation |
| `biometric_callbacks` | To monitor/bypass biometric auth |
| `clipboard_monitor` | To detect sensitive data in clipboard |
| `tls_version_check` | To capture negotiated TLS versions and cipher suites on all connections |
| `data_containerization_check` | To verify app sandbox isolation, storage permissions, and data leakage |

### Enumerate Modules
| Module | When to Use |
|--------|------------|
| `loaded_classes` | To discover app's class structure at runtime |
| `class_methods` | To enumerate methods of a specific class |
| `native_exports` | To discover native library functions |
| `intent_monitor` | To capture all Intent traffic |
| `rasp_detection` | To detect RASP libraries, obfuscation level, anti-hooking, and Frida detection |

### Exploit Modules
| Module | When to Use |
|--------|------------|
| `webview_rce` | To test JavaScript bridge vulnerabilities |
| `deeplink_injection` | To test deeplink handler security |
| `content_provider_dump` | To extract data from content providers |

## Custom Scripts Directory

Place custom `.js` files in `~/.maya/frida-scripts/` to make them available. Name the file to match the module name. Use `file_read` to load and `frida_run_script` to execute.

## Decision Flow

1. Run `framework_detect` to identify the app framework
2. Run `protection_detect` to identify active protections
3. Select bypass modules based on detected protections
4. Compose a single script with all needed bypasses
5. Attach and run the composed script
6. Layer extraction modules based on test objectives
