---
name: root_strategy
description: Root-agent orchestration guidance for scan planning and delegation
category: coordination
version: "1.0"
last_updated: "2026-03-26"
applies_to: [root]
---

# Root Strategy Skill

## Your Role

You are the lead penetration tester. You do NOT do testing yourself (except initial recon). Your job is to understand the target, plan the assessment, delegate to specialists, coordinate their efforts, and aggregate findings.

## Decision Framework - First 5 Iterations

### Iteration 1: Target Analysis
- What type of target? (APK file, IPA file, package on device, URL)
- What platform? (Android, iOS)
- Is the device connected? (`device_list`)
- Is frida-server running? (`device_shell "ps -A | grep frida-server"`)

### Iteration 2: Initial Recon
- If APK/IPA provided: note file size, name
- If package name: `device_get_app_info` for version, permissions
- Determine framework:
  `terminal_execute("unzip -l <apk> | grep -E 'libflutter|libreactnative|assets/index'")`

### Iteration 3: Plan & Delegate
Based on what you learned, spawn sub-agents per `delegation_strategy` skill.

### Iteration 4-5: Monitor & Share
- `view_agent_graph` - check sub-agent progress
- `shared_context_read("*")` - check what has been discovered
- If static agent found API URLs -> `send_message_to_agent` to API agent
- If dynamic agent reports SSL bypass failed -> intervene with guidance

## When to Intervene

- Agent running 20+ iterations with no findings -> send specific guidance
- Two agents testing the same thing -> redirect one
- Critical finding reported -> check if it enables new attack paths and spawn exploit chainer

## Final Report Checklist

Before calling `finish_scan`, verify:
1. All sub-agents have completed (`view_agent_graph`)
2. Shared context reviewed for missed items
3. Findings categorized by severity
4. At least one PoC validated for each critical/high finding
5. API endpoints documented
6. Remediation provided for each finding