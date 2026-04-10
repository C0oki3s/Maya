---
name: quick
description: High-signal quick scan methodology
category: scan_modes
applies_to: [root]
---

# Quick Scan Mode

## Goal

Find the highest-impact vulnerabilities in minimum time. Target: under 30 iterations total.

## What to Test

1. **Transport Security** - SSL pinning bypass, cleartext traffic, certificate validation
2. **Authentication** - Hardcoded credentials, token in SharedPrefs, weak JWT
3. **Exposed Data** - Sensitive data in logs, plaintext storage, world-readable files
4. **API Surface** - IDOR on user-specific endpoints, missing auth on admin routes
5. **Exported Components** - Activities launchable without authentication

## What to Skip

- Full class enumeration and method hooking
- Framework-specific deep analysis
- Exploit chain validation
- Comprehensive IPC fuzzing
- Binary protection assessment

## Agent Allocation

Run as a single agent (no sub-agents) or at most 2:
- Self: static recon + dynamic basics
- Optional: API agent if traffic interception is productive

## Exit Criteria

- At least 3 attack vectors checked
- All critical/high findings have PoC evidence
- Report generated with remediation