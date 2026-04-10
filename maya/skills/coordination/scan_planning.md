---
name: scan_planning
description: Adaptive scan strategy - complexity assessment and agent allocation methodology
category: coordination
version: "1.0"
last_updated: "2026-03-26"
applies_to: [coordination, recon]
---

# Scan Planning Methodology

## Purpose

After initial recon, assess the target's complexity and plan agents/iterations accordingly.

## Step 1: Gather Target Intelligence

Run these commands using basic tools:

1. `terminal_execute("aapt dump badging <apk_path>")` - permissions, activities, services count
2. `terminal_execute("unzip -l <apk_path> | grep '\.so$'")` - native libraries
3. `terminal_execute("jadx -d /tmp/jadx_out <apk_path>")` - decompile
4. `terminal_execute("grep -rn 'frida\|xposed\|magisk\|RootBeer\|SafetyNet\|DexGuard' /tmp/jadx_out/")` - protections
5. `terminal_execute("grep -rn 'flutter\|react.native\|xamarin\|cordova\|ionic' /tmp/jadx_out/")` - framework

## Step 2: Score Complexity

Assess these factors (each 0-10):

| Factor | Low (0-3) | Medium (4-7) | High (8-10) |
|--------|-----------|-------------|-------------|
| **Permissions** | <5 permissions | 5-15 | >15 or dangerous permissions |
| **Components** | <10 activities | 10-30 | >30 activities + services |
| **Native code** | No .so files | Few libraries | Many libraries or heavy JNI |
| **Protections** | None detected | Basic (ProGuard + root check) | Advanced (DexGuard + anti-Frida + integrity) |
| **Framework** | Native Java/Kotlin | React Native/Cordova | Flutter/Unity/KMP |
| **API surface** | Few endpoints | Moderate REST API | Complex API + WebSockets + GraphQL |

Add scores for total (0-60).

## Step 3: Choose Strategy

| Total Score | Strategy | Agents | max_iterations | Focus |
|-------------|----------|--------|----------------|-------|
| < 15 | **Simple** | 1 (self only) | 30 | Static + basic dynamic, no sub-agents needed |
| 15-35 | **Standard** | 3 | 50 per agent | Static analyzer + Dynamic tester + API tester |
| > 35 | **Comprehensive** | 5+ | 80 per agent | Static + Dynamic + API + Framework-specific + Exploit chainer |

## Step 4: Assign Skills Per Agent

### Simple scan - single agent:
Load skills: `frida_operations`, `caido_operations`, `app_reconnaissance`

### Standard scan - 3 agents:
- **Static agent**: `app_reconnaissance`, `static_analysis` skills
- **Dynamic agent**: `frida_operations`, `frida_stealth`, `frida_scripts`
- **API agent**: `caido_operations`, `idor_testing`, `jwt_attacks`

### Comprehensive scan - 5+ agents:
- Add **framework-specific agent** (Flutter/RN/etc.) with platform skills
- Add **exploit chainer agent** with `exploit_chaining` skill
- Allocate more iterations for anti-Frida bypass efforts

## Step 5: Monitor and Redirect

During the scan, every 10 iterations:
- Check `view_agent_graph()` for stuck agents
- If an agent has 0 findings at 50% iterations, reassign it
- If an agent found a critical vuln, spin up an exploit chainer
