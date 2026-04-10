---
name: ssl_pinning_bypass
description: Universal SSL pinning bypass workflow
category: vulnerabilities
version: "1.1"
last_updated: "2026-03-26"
requires: [frida_operations]
---

# SSL Pinning Bypass Skill

1. Attach or spawn target process with Frida.
2. Inject universal bypass hooks for TrustManager and OkHttp.
3. Verify bypass by capturing HTTPS traffic in proxy.
4. Record evidence and fallback techniques if bypass fails.

## Tool Quick Reference

- `frida_attach`: attaches to running target process for runtime hooks.
- `frida_spawn`: launches target process under Frida for early hooks.
- `frida_bypass_ssl_pinning`: injects baseline SSL pinning bypass hooks.
- `verify_ssl_bypass`: validates HTTPS interception path after bypass.
- `caido_start`: starts proxy capture engine.
- `caido_set_scope_from_mobile_traffic`: constrains scope to real app API hosts from captured traffic.
- `caido_assess_mobile_api_security`: hands off to API assessment flow once capture is confirmed.

## Handoff Rule

After SSL bypass succeeds and traffic is visible, immediately run API assessment tools on captured mobile API hosts.
Exclude companion app endpoints and local control interfaces from scope.

Severity guidance:
- If bypass succeeds and sensitive data is exposed, report at least High.
- If bypass attempts are blocked by strong controls, record as resilience note.
