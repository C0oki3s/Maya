---
name: insecure_storage
description: Detection and exploitation of insecure storage on Android and iOS
category: vulnerabilities
version: "1.1"
last_updated: "2026-03-26"
requires: [adb_operations, apktool_operations]
---

# Insecure Storage Skill

Use this skill when the target may store secrets, tokens, PII, or cryptographic material in recoverable locations.

## Discovery Workflow

1. Use `device_get_app_info` to confirm package identifiers, data directories, and backup-relevant metadata.
2. Use `device_dump_app_data` to collect shared preferences, databases, cache files, and exported artifacts.
3. Use `search_decompiled_code` or `mobsf_search_code` to locate storage APIs, hardcoded filenames, and serialization logic.
4. Use `objection_enum_storage` for runtime enumeration when static paths are incomplete.
5. Use `report_vulnerability` only after confirming that sensitive data is stored without platform protections.

## Tool Quick Reference

- `device_get_app_info`: identifies package metadata and filesystem context.
- `device_dump_app_data`: extracts app data directories for analysis.
- `objection_enum_storage`: enumerates app-accessible storage locations at runtime.
- `mobsf_search_code`: searches decompiled code for risky storage usage.
- `search_decompiled_code`: locates files, strings, and API usage in decompiled output.
- `report_vulnerability`: records confirmed insecure storage findings.

## High-Value Checks

- Tokens, session IDs, refresh tokens, API keys, and credentials in plaintext.
- SQLite databases without encryption storing account or transaction data.
- SharedPreferences or plist files holding secrets without Keystore or Keychain protection.
- Backups or exported files that expose internal state.
- Debug logs or crash files containing sensitive values.

## Severity Guidance

- High: credentials, tokens, or payment data stored recoverably.
- Medium: internal data or metadata leaks that materially reduce attack cost.
- Low: non-sensitive data stored weakly without immediate exploit value.

## Remediation

- Use Android Keystore or iOS Keychain for secrets.
- Encrypt sensitive records with device-bound keys.
- Minimize retention and disable insecure backups where appropriate.
- Remove secrets from logs and crash artifacts.