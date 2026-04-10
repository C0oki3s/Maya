---
name: webview_attacks
description: WebView configuration and bridge abuse testing
category: vulnerabilities
version: "1.0"
last_updated: "2026-03-26"
requires: [frida_operations, adb_operations]
applies_to: [dynamic, exploit]
---

# WebView Attacks Skill

Use this skill when the app renders remote or local web content, exposes JS bridges, or mixes trusted and untrusted origins.

## Workflow

1. Search decompiled code for `WebView`, `addJavascriptInterface`, and custom URL handlers.
2. Use `caido_search_traffic` to find WebView-loaded origins and assets.
3. Use `frida_hook_method` or `frida_run_script` to inspect WebSettings and bridge registration at runtime.
4. Validate arbitrary JS execution, file access, origin confusion, or token leakage before reporting.

## High-Value Checks

- JavaScript enabled for untrusted origins.
- Insecure `addJavascriptInterface` exposure.
- File URL access enabling local file theft.
- Token/session data injected into the DOM or headers.

## Remediation

- Limit WebView capabilities for untrusted content.
- Remove dangerous JS bridges or gate them with origin controls.
- Disable file access where not required.