---
name: context_sharing
description: Shared context update and consumption strategy for agent teams
category: coordination
version: "1.0"
last_updated: "2026-03-26"
applies_to: [root, dynamic, static, api, exploit]
---

# Context Sharing

## Purpose

Shared context is the communication channel between agents. It prevents duplicate work and enables cross-pollination of discoveries.

## What to Write

| Discovery Type | Context Key | Example Value |
|----------------|-------------|---------------|
| API endpoints found in code | `discovered_urls` | `["https://api.target.com/v1/login"]` |
| Hardcoded secrets | `hardcoded_secrets` | `[{"type": "api_key", "value": "...", "file": "Config.java"}]` |
| SSL bypass status | `bypasses_active` | `{"ssl": true, "root": true}` |
| Interesting classes for hooking | `interesting_classes` | `["com.target.AuthManager", "com.target.CryptoHelper"]` |
| Device/app metadata | `target_info` | `{"package": "com.target.app", "version": "2.1.0"}` |
| Completed scan phases | `completed_phases` | `["static_manifest", "dynamic_ssl_bypass"]` |

## Rules

1. **Write only validated discoveries** - no guesses or speculation.
2. **Read shared context before each major phase** - another agent may have found something useful.
3. **Use concise structured data** - JSON-serializable facts, not prose.
4. **Include source attribution** - which agent wrote this and when.
5. **Do not overwrite** - append to existing lists, don't replace them.

## Workflow

### At Phase Start
```
shared_context_read("*")
```
Check for new intel from other agents before starting work.

### On Discovery
```
shared_context_write("discovered_urls", '["https://api.target.com/v1/users"]')
```
Share immediately so other agents can act on it.

### Cross-Agent Signals

- Static agent finds API URLs -> API agent can start testing those endpoints
- Dynamic agent confirms SSL bypass -> API agent can begin traffic interception
- API agent finds IDOR -> Exploit agent can build a chain
- Any agent finds a hardcoded key -> all agents should check where it's used