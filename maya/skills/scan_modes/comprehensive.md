---
name: comprehensive
description: Deep comprehensive scan methodology
category: scan_modes
applies_to: [root]
---

# Comprehensive Scan Mode

## Goal

Full attack-surface coverage including framework-specific analysis, exploit chaining, and tampering resilience. Target: 80 iterations per agent.

## What to Test

1. **All Standard Mode tests** - static, dynamic, API, IPC, storage
2. **Framework-Specific** - Flutter (if detected): reFlutter, libapp.so analysis; React Native: JS bundle extraction, bridge hooking; Xamarin: assembly decompilation
3. **Exploit Chains** - Combine findings into multi-step attack chains (credential theft + IDOR = account takeover)
4. **Binary Protections** - Anti-tampering, anti-debug, code obfuscation assessment
5. **Advanced IPC** - Intent fuzzing, content provider SQL injection, broadcast spoofing
6. **Crypto Analysis** - Algorithm identification, key extraction, hardcoded IV/salt detection
7. **WebView Attacks** - JavaScript interface exposure, file:// access, deeplink injection via WebView

## Agent Allocation

Spawn 5+ sub-agents:
1. **Static Analyzer** - standard skills + `binary_protections, code_tampering`
2. **Dynamic Tester** - standard skills + `insecure_crypto, bypass_techniques`
3. **API Discoverer** - standard skills + `jwt_attacks, idor_testing`
4. **Framework Specialist** - if detected: `flutter_analysis` / `react_native_analysis` / `xamarin_analysis`
5. **Exploit Chainer** - skills: `exploit_chainer, exploit_techniques, frida_operations, caido_operations`

## Exit Criteria

- All 7 categories above checked
- Every critical/high finding has validated PoC
- Exploit chains documented with step-by-step reproduction
- Framework-specific findings included
- Comprehensive report with CVSS scores and remediation priorities