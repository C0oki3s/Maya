---
name: ipc_vulnerabilities
description: Android and iOS inter-process communication abuse testing
category: vulnerabilities
version: "1.0"
last_updated: "2026-03-26"
requires: [adb_operations]
applies_to: [dynamic, exploit]
---

# IPC Vulnerabilities Skill

Use this skill for exported Android components, deeplinks, URL schemes, intents, content providers, and iOS URL handler abuse.

## Workflow

1. Use `analyze_manifest` and `mobsf_get_results` to identify exported components and intent filters.
2. Use `device_shell` to invoke activities, services, broadcasts, or content providers with crafted input.
3. Use `frida_hook_method` to observe intent extras, URL parameters, and authorization checks at runtime.
4. Report only when unauthorized actions, data exposure, or privilege escalation are confirmed.

## High-Value Checks

- Exported activities processing attacker-controlled extras.
- Broadcast receivers triggering sensitive flows without signature protection.
- Content providers exposing private records.
- Deeplinks that bypass login or trust user-controlled redirect targets.

## Remediation

- Remove unnecessary exports.
- Enforce permission checks at every entry point.
- Validate all inbound URIs, extras, and caller identity.