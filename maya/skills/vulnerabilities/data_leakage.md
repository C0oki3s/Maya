---
name: data_leakage
description: Sensitive data exposure through logs, screenshots, clipboard, and backups
category: vulnerabilities
version: "1.0"
last_updated: "2026-03-26"
requires: [adb_operations]
applies_to: [dynamic, static]
---

# Data Leakage Skill

Use this skill when evaluating whether sensitive information escapes intended trust boundaries.

## Workflow

1. Use `collect_logs` through the companion flow or `device_shell` log commands to inspect runtime logging.
2. Inspect screenshots, notifications, caches, temp files, and exported backups.
3. Check whether secrets appear in API traffic, local storage, or UI surfaces unnecessarily.

## High-Value Checks

- Access tokens or PII in logs.
- Sensitive screens capturable without secure flags.
- Clipboard leakage.
- Backups containing decryptable app data.

## Remediation

- Redact secrets from logs.
- Prevent screenshots for highly sensitive screens.
- Limit retention and backup exposure.