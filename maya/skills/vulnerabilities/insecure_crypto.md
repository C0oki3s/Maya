---
name: insecure_crypto
description: Weak cryptography and key handling assessment workflow
category: vulnerabilities
version: "1.1"
last_updated: "2026-03-26"
requires: [frida_operations, apktool_operations]
---

# Insecure Crypto Skill

Use this skill for identifying weak algorithms, static IVs, hardcoded keys, unsafe randomness, and decryptable data flows.

## Discovery Workflow

1. Use `mobsf_search_code` or `search_decompiled_code` to locate `Cipher`, `MessageDigest`, `SecretKeySpec`, and crypto helper wrappers.
2. Use `frida_trace_crypto` to capture algorithms, keys, IVs, and plaintext at runtime.
3. Use `frida_hook_method` for custom wrappers when standard hooks are insufficient.
4. Use `report_vulnerability` after correlating static weaknesses with runtime evidence.

## Tool Quick Reference

- `mobsf_search_code`: finds suspicious crypto usage in decompiled code.
- `search_decompiled_code`: broad grep-style search for keys, algorithms, and wrappers.
- `frida_trace_crypto`: hooks common crypto primitives to expose material and usage.
- `frida_hook_method`: targets proprietary helper methods around crypto.
- `report_vulnerability`: records validated crypto weaknesses.

## High-Value Checks

- AES/ECB usage.
- Static keys or IVs embedded in code or resources.
- Predictable random seeds or weak PRNG usage.
- MD5 or SHA-1 used for security-sensitive integrity or password derivation.
- Homegrown encryption layers around sensitive storage or transport.

## Severity Guidance

- High: recoverable keys or plaintext exposure enabling direct compromise.
- Medium: weak algorithm choice with realistic exploit preconditions.
- Low: legacy or defense-in-depth weakness without immediate exploit path.

## Remediation

- Use platform-backed key storage.
- Prefer modern authenticated encryption modes.
- Generate fresh IVs and nonces per operation.
- Eliminate hardcoded secrets and replace weak hashes for security use cases.