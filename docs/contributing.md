# Contributing to Maya

Thank you for your interest in making Maya better! This guide covers everything you need to contribute — from fixing a typo to adding a new tool module.

---

## Table of Contents

- [Development Setup](#development-setup)
- [Code Conventions](#code-conventions)
- [Adding a New Tool](#adding-a-new-tool)
- [Adding a New Skill](#adding-a-new-skill)
- [Adding Frida Scripts](#adding-frida-scripts)
- [Writing Tests](#writing-tests)
- [Pull Request Process](#pull-request-process)
- [Skill Authoring Guide](#skill-authoring-guide)
- [Architecture Overview](#architecture-overview)

---

## Development Setup

```bash
# Clone
git clone https://github.com/USER/MOBSEC.git
cd MOBSEC

# Virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1

# Install with dev dependencies
pip install -e ".[dev]"

# Install linter
pip install ruff

# Verify
pytest -q
maya --help
```

---

## Code Conventions

### Tools — The Rules

Every tool MUST follow these patterns:

```python
from maya.tools.registry import register_tool

@register_tool(sandbox_execution=True)
def my_scan_tool(target: str, depth: str = "3") -> dict:
    """Scan target for X. Runs inside sandbox."""
    try:
        result = subprocess.run(
            ["scanner", target, "--depth", depth],
            capture_output=True, text=True, timeout=120
        )
        return {"status": "ok", "stdout": result.stdout, "exit_code": result.returncode}
    except Exception as exc:
        return {"error": str(exc)}
```

| Rule | Why |
|------|-----|
| Use `@register_tool(sandbox_execution=True\|False)` | Auto-generates XML schema, registers in global registry |
| Return `dict` always | `{"status": "ok", ...}` or `{"error": "msg"}` — LLM reads this as observation |
| Never raise exceptions | Catch everything, return error dict. Agent self-corrects from error messages |
| Include a docstring | Becomes the `<description>` in the XML schema the LLM reads |
| Use `subprocess.run()` with `timeout=` | Never leave commands running forever |
| Import in `maya/tools/__init__.py` | The `@register_tool` decorators fire on import |

### Agents

- Subclass `BaseAgent`
- Implement `build_system_prompt()` and `on_scan_complete()`
- Use `@dataclass(slots=True)` for data classes
- Use `AgentState` as the single source of truth

### General Python

- Async-first (`asyncio`, not threading)
- Type hints on all function signatures
- No hardcoded credentials — use env vars or config
- Use `asyncio.Lock()` for shared mutable state

### Linting

```bash
# Check
ruff check .
ruff format --check .

# Auto-fix
ruff check --fix .
ruff format .
```

---

## Adding a New Tool

### Step 1: Create the tool module

```python
# maya/tools/my_tool.py

import subprocess
from maya.tools.registry import register_tool

@register_tool(sandbox_execution=True)
def my_tool_scan(target: str, output_format: str = "json") -> dict:
    """Run my_tool against target. Returns scan results."""
    try:
        result = subprocess.run(
            ["my_tool", "scan", target, "-f", output_format],
            capture_output=True, text=True, timeout=300
        )
        return {"status": "ok", "stdout": result.stdout, "exit_code": result.returncode}
    except Exception as exc:
        return {"error": str(exc)}
```

### Step 2: Register it

```python
# maya/tools/__init__.py — add this import
from maya.tools import my_tool  # noqa: F401
```

### Step 3: Add a companion skill

```markdown
<!-- maya/skills/tools/my_tool_operations.md -->
---
name: my_tool_operations
description: "Operational guide for my_tool scanning"
category: tools
applies_to: [static, dynamic]
---

# my_tool Operations

## When to Use
- Use my_tool_scan when you need to...

## Prerequisites
- my_tool must be installed in the sandbox (it is)
- Target must be...

## Common Patterns
1. Quick scan: `my_tool_scan(target="com.app", output_format="json")`
2. Deep scan: `my_tool_scan(target="com.app", output_format="detailed")`

## Output Interpretation
- Exit code 0: scan complete
- Exit code 1: target not found
- Look for "CRITICAL" in stdout for high-severity findings
```

### Step 4: Write tests

```python
# tests/test_my_tool.py

from maya.tools.my_tool import my_tool_scan

def test_my_tool_scan_returns_dict():
    result = my_tool_scan(target="test.apk")
    assert isinstance(result, dict)
    assert "status" in result or "error" in result
```

### Step 5: Submit PR

---

## Adding a New Skill

Skills are Markdown files with YAML frontmatter. Place them in the correct category:

| Category | What it teaches | Example |
|----------|----------------|---------|
| `vulnerabilities/` | What to find | `insecure_storage.md`, `ssl_pinning_bypass.md` |
| `tools/` | How to use a tool | `frida_operations.md`, `caido_operations.md` |
| `frameworks/` | Framework-specific | `flutter_analysis.md`, `react_native_analysis.md` |
| `platforms/` | Platform internals | `android_internals.md`, `ios_internals.md` |
| `agents/` | Agent behavior | `root_orchestrator.md`, `dynamic_tester.md` |
| `coordination/` | Multi-agent patterns | `delegation_strategy.md`, `context_sharing.md` |
| `scan_modes/` | Scan depth config | `quick.md`, `comprehensive.md` |

### Skill Template

```markdown
---
name: my_skill
description: "One-line description of what this skill teaches"
category: vulnerabilities
version: "1.0"
last_updated: "2026-04-01"
requires: [frida_operations]           # Auto-loaded dependencies
applies_to: [dynamic, static]          # Which agent roles use this
platform: [android, ios]               # Platform filter
frida_version_tested: "16.5.x"         # Optional: version compatibility
---

# My Skill Name

## Overview
What this skill is about.

## Detection Steps
1. First, do X using `tool_name`
2. Then check Y
3. If Z, the app is vulnerable

## Exploitation
How to exploit the finding once detected.

## Remediation
What developers should fix.
```

### Verify

```bash
maya --list-skills
# Should show your new skill
```

---

## Adding Frida Scripts

Pre-built scripts go in `assets/frida-scripts/<category>/`:

| Category | Purpose |
|----------|---------|
| `bypass/` | Bypass security controls (root detection, SSL pinning, etc.) |
| `enumerate/` | Enumerate app internals (classes, methods, intents) |
| `exploit/` | Exploit vulnerabilities (WebView RCE, deeplink injection) |
| `extract/` | Extract data (crypto keys, SharedPreferences, SQLite) |
| `ios/` | iOS-specific scripts |

### Script Template

```javascript
// assets/frida-scripts/extract/my_extractor.js
'use strict';

Java.perform(function() {
    // Hook target class
    var TargetClass = Java.use('com.example.TargetClass');

    TargetClass.sensitiveMethod.implementation = function(arg) {
        console.log('[*] sensitiveMethod called with: ' + arg);
        var result = this.sensitiveMethod(arg);
        console.log('[*] Result: ' + result);
        return result;
    };
});
```

---

## Writing Tests

### Test Location

All tests go in `tests/`. Name them `test_<module>.py`.

### What to Test

| Component | Test strategy |
|-----------|--------------|
| Tools | Call the function, assert it returns a dict with `status` or `error` |
| Skills loader | Verify skill files parse correctly, dependencies resolve |
| Agent loop | Mock LLM responses, verify tool invocation |
| LLM config | Verify env/file/CLI precedence |
| Parser | Feed XML strings, verify parsed tool calls |

### Running Tests

```bash
# All tests (except device-gated)
pytest -q -k "not integration"

# Specific file
pytest tests/test_my_tool.py -v

# Integration tests (needs connected device)
pytest -q -m integration
```

---

## Pull Request Process

### Before Submitting

- [ ] Code follows conventions above
- [ ] Tests pass: `pytest -q`
- [ ] Linter passes: `ruff check . && ruff format --check .`
- [ ] New tools are imported in `maya/tools/__init__.py`
- [ ] New skills have proper YAML frontmatter
- [ ] Documentation updated if needed

### PR Requirements

| Requirement | Description |
|-------------|-------------|
| **1 approving review** | From a maintainer |
| **Passing CI** | Lint + tests + Docker build check |
| **CodeQL clean** | No new security alerts |
| **No conflicts** | Rebase on latest `main` |

### Branch Naming

```
feat/frida-gadget-tool
fix/checkpoint-resume-crash
docs/skill-authoring-guide
chore/update-dependencies
```

### Review Timeline

- Acknowledgment within **48 hours**
- Full review within **1 week**
- Security-critical PRs are prioritized

---

## Skill Authoring Guide

### The Golden Rule

**Tools are dumb executors. Skills are the brain.**

- A tool takes parameters → runs a command → returns raw output
- A skill teaches the agent WHEN to use tools, in WHAT order, with WHAT parameters, and HOW to interpret results

### Good vs Bad Skills

**Bad** (too generic):
```markdown
# SSL Pinning
SSL pinning prevents MITM attacks. To bypass it, use Frida.
```

**Good** (actionable, step-by-step):
```markdown
# SSL Pinning Bypass

## Detection
1. Run `frida_run_script` with `ssl_pinning_bypass.js` against the target
2. If the script loads but no hooks fire, the app uses custom pinning
3. Check logcat for "SSL handshake" errors

## Bypass Sequence
1. First try: `frida_run_script(package="com.app", script="bypass/ssl_pinning_bypass.js")`
2. If that fails, try Objection: `objection_run(package="com.app", command="android sslpinning disable")`
3. If both fail, decompile and search for pinning libraries:
   - `apk_search(keyword="CertificatePinner")` → OkHttp
   - `apk_search(keyword="TrustManager")` → Custom
4. Write a targeted Frida hook for the specific implementation
```

### Skill Dependencies

Use the `requires` field so loading one skill auto-loads its dependencies:

```yaml
requires: [frida_operations, adb_operations]
```

When the agent loads `ssl_pinning_bypass`, it automatically gets `frida_operations` and `adb_operations` too.

---

## Architecture Overview

For contributors who want to understand the system before diving in:

```
CLI (click) → ScanConfig → Root MayaAgent
  ├── Sub-Agent (Static)    ← spawned via create_agent tool
  ├── Sub-Agent (Dynamic)
  ├── Sub-Agent (API)
  └── Sub-Agent (Exploit)
       Each agent: Think → Plan → Act → Observe
       Each agent: own Docker sandbox + tool_server
       Tools: @register_tool → XML schema → executor
       Skills: Markdown → Jinja template → system prompt
```

Read the [Architecture doc](01-ARCHITECTURE.md) for the full deep-dive.
