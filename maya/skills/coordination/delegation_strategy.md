---
name: delegation_strategy
description: Multi-agent delegation patterns and task granularity guidance
category: coordination
version: "1.0"
last_updated: "2026-03-26"
applies_to: [root]
---

# Delegation Strategy

## When to Delegate vs Self-Execute

| Situation | Action |
|-----------|--------|
| Task needs specialist tooling (Frida, Caido, MobSF) | Delegate to specialist agent |
| Task can be done in 1-2 tool calls | Do it yourself - delegation overhead not worth it |
| Two independent workstreams can run in parallel | Delegate both |
| Task depends on output of another task | Wait for predecessor, then delegate |

## Agent Allocation Rules

1. NEVER create more than 5 sub-agents at once - coordination overhead increases quadratically.
2. Every sub-agent MUST have at least one tool skill AND one vulnerability skill.
3. Task descriptions must be SPECIFIC and measurable:
   - Good: "Bypass SSL pinning and hook auth methods on com.target.app, report all discovered tokens"
   - Bad: "Do dynamic testing"
4. Assign `frida_operations` to ANY agent that will use Frida tools.
5. Assign `caido_operations` to ANY agent that will intercept traffic.

## Spawn Pattern

```
create_agent(
  task="<specific measurable task>",
  name="<role>_<target_focus>",
  skills="<agent_skill>,<tool_skill1>,<vuln_skill1>"
)
```

## Standard Delegation Template

### Always Spawn (for any non-trivial target)

1. **Static Analyzer** - skills: `static_analyzer, apktool_operations, mobsf_operations, insecure_storage, insecure_crypto`
2. **Dynamic Tester** - skills: `dynamic_tester, frida_operations, objection_operations, ssl_pinning_bypass, auth_bypass`
3. **API Discoverer** - skills: `api_discoverer, caido_operations, api_security, frida_operations`

### Conditionally Spawn

- Flutter detected -> Flutter specialist: `flutter_analysis, reflutter_operations, frida_operations`
- React Native detected -> RN specialist: `react_native_analysis, frida_operations`
- Complex auth -> Auth specialist: `auth_bypass, api_security, frida_operations`
- Critical findings ready -> Exploit chainer: `exploit_chainer, frida_operations, caido_operations`

## Monitoring Active Agents

- Check progress every 5-10 iterations: `view_agent_graph`
- If agent stalls (20+ iterations, no findings) -> `send_message_to_agent` with specific guidance
- If two agents overlap -> redirect one to a different attack surface
- If critical finding reported -> assess whether to spawn exploit chainer