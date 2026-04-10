---
name: auth_bypass
description: Authentication and authorization bypass testing workflow
category: vulnerabilities
version: "1.1"
last_updated: "2026-03-26"
requires: [frida_operations, caido_operations]
---

# Auth Bypass Skill

Use this skill when testing login flows, session state, access control boundaries, biometric gates, or PIN protections.

## Discovery Workflow

1. Use `caido_search_traffic` or `report_api_endpoint` outputs to identify login, refresh, profile, and privilege-sensitive endpoints.
2. Use `frida_hook_method` or `frida_run_script` to inspect client-side auth checks, token handling, and gatekeeper logic.
3. Use `verify_proxy_path` and `verify_ssl_bypass` before relying on intercepted traffic.
4. Use `caido_replay_request` or `caido_assess_mobile_api_security` to test token swapping, user identifier changes, and privilege escalation paths.
5. Use `report_vulnerability` once authorization impact is verified.

## Tool Quick Reference

- `frida_hook_method`: hooks client-side decision points around auth or session handling.
- `frida_run_script`: executes custom runtime bypass logic.
- `caido_search_traffic`: finds auth flows and session-bearing requests.
- `caido_replay_request`: replays modified requests to test broken authorization.
- `caido_assess_mobile_api_security`: drives endpoint assessment from real mobile traffic.
- `report_vulnerability`: records confirmed auth bypass issues.

## High-Value Checks

- IDOR through modified user identifiers.
- Session fixation or token reuse across accounts.
- Biometric or local PIN checks enforced only on the client.
- Access to privileged endpoints after logout or role downgrade.
- JWT claims trusted without server-side enforcement.

## Severity Guidance

- Critical: account takeover or cross-tenant admin access.
- High: horizontal access to other users' data or actions.
- Medium: local or limited bypass that still requires prior access.

## Remediation

- Enforce authorization on every sensitive server action.
- Bind sessions and tokens to server-side context.
- Avoid trusting client-side auth state for privileged decisions.
- Revalidate biometric or PIN-protected actions on the server where applicable.