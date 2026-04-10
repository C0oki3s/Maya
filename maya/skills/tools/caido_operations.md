---
name: caido_operations
description: Caido proxy operations - HTTPQL syntax, SDK methods, scope handling, and API assessment workflow
category: tools
version: "2.0"
last_updated: "2026-03-26"
requires: [frida_operations]
applies_to: [api, dynamic, exploit]
---

# Caido Operations Guide

## Prerequisites

1. Ensure SSL bypass is active before expecting HTTPS visibility.
2. Start Caido and verify endpoint map refresh succeeds.
3. Scope traffic to mobile-app API hosts only.

## The Generic Tool

All Caido interaction uses `caido_command(method, params)`. The method is either:
- An API endpoint path (e.g. `/api/intercept/toggle`)
- A short method name (auto-prefixed with `/api/`)

## HTTPQL Query Syntax

HTTPQL is Caido's query language for filtering traffic:

```
req.method.eq:"POST"          - exact match
req.path.cont:"/api"          - contains
req.host.cont:"target.com"    - host filter
resp.code.gte:400              - status code range
resp.body.cont:"token"         - response body search
req.header.name:"Authorization" - header presence
```

Combine with AND / OR / NOT:
```
req.method.eq:"POST" AND req.path.cont:"/api" AND NOT req.host.cont:"google"
```

### Common HTTPQL Patterns for Mobile Testing

| Goal | Query |
|------|-------|
| All POST requests to target | `req.method.eq:"POST" AND req.host.cont:"target.com"` |
| Auth-bearing requests | `req.header.name:"Authorization"` |
| Find API endpoints | `req.path.cont:"/api" AND resp.code:200` |
| Find error responses | `resp.code.gte:400 AND req.host.cont:"target"` |
| Look for tokens in response | `resp.body.cont:"token" OR resp.body.cont:"jwt"` |
| WebSocket traffic | Use `caido_get_websocket_traffic` |
| Requests with IDs | `req.path.regex:/[0-9]+/` |

## Key Caido API Methods

### Traffic Search
```
caido_command(method="/api/http/history/search", params='{"query": "req.host.cont:\"target\""}')
```

### Replay Requests (for IDOR/auth testing)
```
caido_command(method="/api/replay/send", params='{"requestId": "<id>", "modifications": {"headers": {"Authorization": "Bearer <other_token>"}}}')
```

### Intercept Toggle
```
caido_command(method="/api/intercept/toggle", params='{"enabled": true, "rules": "api.target.com"}')
```

### Match and Replace
```
caido_command(method="/api/match-replace/create", params='{"match": "old-token", "replace": "new-token", "location": "header"}')
```

### Export Findings
```
caido_command(method="/api/findings/export", params='{}')
```

### Set Scope
```
caido_command(method="/api/scope/set", params='{"scope": "*.target.com"}')
```

### Diff Two Requests (IDOR testing)
```
For request A: caido_command(method="/api/http/request/<id_a>", params='{}')
For request B: caido_command(method="/api/http/request/<id_b>", params='{}')
Compare the two responses manually.
```

### WebSocket Analysis
```
caido_command(method="/api/websocket/search", params='{"filter": "", "limit": 100}')
```

## Workflow: Traffic Interception Setup

Follow this sequence using basic tools:

1. Apply SSL pinning bypass (see frida_stealth.md or frida_scripts.md)
2. Start Caido: `caido_start(listen="0.0.0.0:8080")`
3. Configure device proxy: `device_shell("settings put global http_proxy <proxy_host>:8080")`
4. Set scope: `caido_set_scope(scope="*.target.com")` - use wildcards for subdomains
5. Exercise app on device
6. Search traffic: `caido_search_traffic(query="req.host.cont:\"target\"")`

If step 6 returns empty:
- Check proxy: `device_shell("settings get global http_proxy")`
- Check Caido health: `terminal_execute("curl localhost:8080/health")`
- Verify SSL bypass is active

## Scoping to Mobile API Hosts

When setting scope, exclude non-target traffic:
- Exclude: localhost, 127.0.0.1, host.docker.internal, companion app hosts
- Include only: the app's actual backend API domains
- Use `shared_context_read` to get discovered URLs from other agents
- Build scope expression: `caido_set_scope(scope="*.api.target.com OR *.backend.target.com")`

## API Security Assessment Workflow

After traffic is captured, assess endpoints systematically:
1. Export sitemap: `caido_export_sitemap()` to get all discovered endpoints
2. For each endpoint, test authorization: replay with different tokens via `caido_replay_request`
3. For sensitive endpoints, fuzz parameters: `caido_automate_fuzz(endpoint="...", payloads="sqli,xss,idor")`
4. Create findings for confirmed issues: `caido_create_finding(title="...", severity="...", description="...")`

## Rule

Never prioritize companion or localhost control-plane traffic as API findings.