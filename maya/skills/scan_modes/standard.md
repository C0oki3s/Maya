---
name: standard
description: Balanced standard scan methodology
category: scan_modes
applies_to: [root]
---

# Standard Scan Mode

## Goal

Balanced coverage across static, dynamic, and API testing. Target: 50 iterations per agent.

## What to Test

1. **Static Analysis** - Manifest review, MobSF automated scan, grep for secrets, dependency audit
2. **Dynamic Testing** - SSL bypass, root detection bypass, storage audit, crypto hooking, auth flow hooking
3. **API Testing** - Endpoint discovery, IDOR testing, auth bypass, input validation
4. **IPC** - Exported components, deeplink handling, content provider queries
5. **Storage** - SharedPrefs, databases, keychain, file permissions

## What to Skip

- Exhaustive exploit chain construction (defer to comprehensive)
- Framework-specific deep dives unless framework detected
- Binary-level reverse engineering

## Agent Allocation

Spawn 3 sub-agents:
1. **Static Analyzer** - skills: `static_analyzer, apktool_operations, mobsf_operations, insecure_storage, insecure_crypto`
2. **Dynamic Tester** - skills: `dynamic_tester, frida_operations, objection_operations, ssl_pinning_bypass, auth_bypass`
3. **API Discoverer** - skills: `api_discoverer, caido_operations, api_security`

## Exit Criteria

- All 5 categories above checked
- Findings validated with evidence
- Cross-agent discoveries shared and followed up
- Final report with severity ratings and remediation