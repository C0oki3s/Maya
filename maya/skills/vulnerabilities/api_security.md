---
name: api_security
description: API endpoint discovery and abuse testing workflow
category: vulnerabilities
version: "1.1"
last_updated: "2026-03-26"
requires: [caido_operations, frida_operations]
---

# API Security Skill

1. Map endpoints from static strings and runtime traffic.
2. Test authZ/authN boundaries: IDOR, broken object-level auth, mass assignment.
3. Validate input handling: SQLi, command injection, SSRF, traversal.
4. Prioritize exploit chains and provide concrete remediation.

## Tool Quick Reference

- `caido_start`: starts Caido headless proxy so mobile traffic can be intercepted.
- `caido_refresh_endpoint_map`: discovers verified control endpoints from a running Caido instance.
- `caido_set_scope_from_mobile_traffic`: scopes Caido to real mobile-app API hosts only.
- `caido_search_traffic`: queries captured traffic using HTTPQL-style filters.
- `caido_export_sitemap`: exports discovered endpoints from captured traffic.
- `caido_assess_mobile_api_security`: orchestrates endpoint fuzzing on captured mobile API traffic.
- `caido_automate_fuzz`: runs payload-based API fuzzing for injection and authz weaknesses.
- `report_api_endpoint`: stores endpoint metadata for cross-agent usage and reporting.
- `report_vulnerability`: records validated API findings with severity and evidence.

## Mobile-Traffic-First Rule

Always derive API targets from captured mobile app traffic after SSL unpinning.
Do not scope assessment to companion endpoints, localhost control APIs, or scanner control plane URLs.

Reporting:
- Include impacted endpoint, auth context, reproducible request, and response evidence.
