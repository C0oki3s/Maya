---
name: binary_protections
description: Binary hardening and obfuscation assessment guidance
category: vulnerabilities
version: "1.0"
last_updated: "2026-03-26"
requires: [apktool_operations]
applies_to: [static]
---

# Binary Protections Skill

Use this skill to assess the difficulty of static and dynamic reverse engineering against the shipped binary.

## Workflow

1. Use `apktool_decompile`, `jadx_decompile`, `extract_strings`, and framework-specific tools.
2. Check for symbol stripping, string protection, tamper detection, and anti-hooking logic.
3. Correlate protection gaps with actual exploitability, not just presence or absence of obfuscation.

## Severity Guidance

- Usually informational unless the lack of protection materially enables a confirmed exploit chain.

## Remediation

- Apply consistent release hardening.
- Remove debug artifacts and reduce symbolic leakage.
- Combine obfuscation with server-side trust controls.