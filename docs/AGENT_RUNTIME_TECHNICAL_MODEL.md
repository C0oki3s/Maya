# Maya Codebase Technical Model (Root-Agent Focus)

## 1) Scope of This Model

This document models how the repository currently works in code, with emphasis on:

- end-to-end execution flow
- how application testing is performed
- which tools are used and how they are dispatched
- how information is passed back to the root agent
- what is actually tested today

Repository snapshot modeled from source under:

- `maya/` (Python runtime/agent/tool stack)
- `companion_app/android/` and `companion_app/ios/` (device-side command execution)
- `containers/`, `scripts/`, `tests/`, `.github/workflows/`

## 2) High-Level Runtime Architecture

```text
CLI (maya.main:cli)
  -> builds ScanConfig + LLMConfig
  -> creates root MayaAgent
  -> root BaseAgent.initialize()
       -> AgentState init
       -> DockerRuntime.create_sandbox()
       -> system prompt render (Jinja + tools + skills)
  -> BaseAgent.agent_loop()
       Think/Plan/Act/Observe iterations
       -> LLM response
       -> parse XML tool calls
       -> execute tools (sandbox/local)
       -> feed tool results back into conversation
  -> finish_scan / agent_finish
  -> tracer persists findings + reports
```

Primary control files:

- `maya/main.py`
- `maya/agents/base_agent.py`
- `maya/agents/maya_agent.py`
- `maya/tools/executor.py`

## 3) Bootstrapping and Scan Startup

### 3.1 CLI Entry

`maya/main.py` performs:

1. Argument parsing (`--target`, `--package`, `--device`, `--model`, `--scan-mode`, `--skills`, etc.)
2. Target/platform normalization
3. `ScanConfig` creation (`maya/models.py`)
4. `LLMConfig.load().apply_overrides(...)` and `LLMClient` creation
5. LLM connectivity check via `await llm.validate()`
6. Root `MayaAgent` construction and optional checkpoint resume

It supports:

- headless mode (`-n`) with stderr progress stream
- Textual UI mode (`maya/ui/app.py`)

### 3.2 Root Agent Construction

`maya/agents/maya_agent.py`:

- selects role-specific tool modules (`_role_modules`)
- resolves role default skills (`_role_default_skills`)
- renders `maya/agents/MayaAgent/system_prompt.jinja`

System prompt includes:

- identity/methodology
- target/device metadata
- XML schemas for allowed tools (`get_tools_prompt`)
- loaded skill content (Markdown injected into prompt)

## 4) Agent Loop (Think -> Tool -> Observe)

`BaseAgent.agent_loop()` in `maya/agents/base_agent.py`:

1. Increment iteration counter
2. Optional reflection every 5 iterations (`_check_progress`)
3. Build conversation history from `AgentState.messages`
4. Optional context compression (`MemoryCompressor`)
5. `llm.generate(...)`
6. Normalize tool-call format (`normalize_tool_format`)
7. Parse calls (`parse_tool_invocations`)
8. Execute calls (`process_tool_invocations`)
9. Append each tool result back as a synthetic `user` message via `<tool_result ...>`
10. Save checkpoint every N iterations (default 5)
11. Stop on:
   - `finish_scan` -> `{"scan_completed": true}`
   - `agent_finish` -> `{"agent_completed": true}`
   - max iterations / repeated failures

## 5) Tool System and Dispatch

### 5.1 Registration and Schema

`maya/tools/registry.py`:

- `@register_tool(sandbox_execution=...)` registers tool function
- introspects signature to auto-build parameter schema
- auto-generates XML tool contract for prompt injection

### 5.2 Execution Path

`maya/tools/executor.py`:

1. Validate tool exists
2. Validate required/allowed params against signature-derived schema
3. Emit telemetry events (`TOOL_CALL_START`, completion/error)
4. Apply throttling (`maya/llm/request_queue.py`) for selected tool patterns
5. Execute:
   - sandbox HTTP call (`_execute_tool_in_sandbox`) if enabled and sandbox endpoint exists
   - otherwise local direct Python function call (`_execute_tool_locally`)

### 5.3 Sandbox Behavior in Current Code

Sandbox infra is defined (`maya/runtime/docker_runtime.py`, `maya/runtime/tool_server.py`) but the default container entrypoint in `containers/Dockerfile.sandbox` is `maya` (CLI), not a `uvicorn` tool server process.

Implication in current flow:

- `DockerRuntime.create_sandbox()` often falls back to dry-run info (`server_url=""`) when health/registration fails.
- If `server_url` is empty, executor automatically executes tools locally.

So `sandbox_execution=True` means "eligible for sandbox", but may still run local depending on runtime health.

## 6) How App Testing Is Performed (Tooling Layers)

### 6.1 Static Analysis Layer

Main modules:

- `maya/tools/apk_tool.py`
- `maya/tools/mobsf_tool.py`
- `maya/tools/terminal.py` (fallback shell utilities)

Typical operations:

- APK decompile (`apktool_decompile`, `jadx_decompile`)
- Manifest parsing (`analyze_manifest`)
- regex/code search (`search_decompiled_code`, `semgrep_scan`)
- binary strings/class dump for iOS

### 6.2 Dynamic Device Layer

Main modules:

- `maya/tools/device_bridge.py`
- `maya/tools/frida_tool.py`
- `maya/tools/objection_tool.py`
- `maya/tools/verification.py`

Operations:

- ADB shell/install/pull/push/info/proxy control
- Frida attach/spawn/script execution
- Objection command execution
- runtime checks (device connected, frida visibility, proxy/SSL bypass checks)

### 6.3 API/Traffic Layer

Main modules:

- `maya/tools/caido_tool.py`
- `maya/tools/device_bridge.py` (proxy/companion path)

Operations:

- Caido start and endpoint discovery/probing
- traffic search/replay/fuzz/scope/finding operations

### 6.4 Companion App Command Layer (On-Device)

Android companion:

- HTTP server in `companion_app/android/.../Application.kt` (`/health`, `/command`)
- command fan-out in `CommandRouter.kt`
- execution primitives in module classes (PackageAnalyzer, ActivityInspector, ContentProviderInspector, ServiceInspector, DeviceInfo, VulnerabilityScanner, etc.)

Python bridge:

- `device_bridge.companion_app_command(...)` and `drozer_tool.*` send JSON commands to companion endpoint

iOS companion:

- `companion_app/ios/CompanionServer.swift` is currently scaffold-level (returns hints/stub responses)

### 6.5 Compliance/Automation Layer

`maya/tools/compliance_tool.py` runs predefined Frida scripts from `assets/frida-scripts/` grouped by:

- device integrity
- code protection
- encryption
- transport security

## 7) How Information Is Passed to the Root Agent

There are multiple channels:

### Channel A: Conversation Tool Results (primary reasoning loop)

- After each tool call, executor result is converted to `<tool_result ...>` text.
- This is appended into current agent conversation as a `user` message.
- The next LLM turn consumes it.

This is the main observe-feedback mechanism.

### Channel B: AgentState structured fields

Each agent keeps its own:

- `findings`
- `api_endpoints`
- `notes`
- `todo_items`
- `messages`

Recorded mainly via:

- `report_vulnerability`
- `report_api_endpoint`
- `add_note`
- `update_todo`

### Channel C: Shared Global Context

`maya/tools/shared_context.py` provides process-global key/value context:

- `shared_context_write(key, value)`
- `shared_context_read(key?)`

Used for cross-agent handoff of discovered artifacts (URLs, endpoints, classes, notes).

### Channel D: Direct Inter-Agent Messaging

`maya/tools/agents_graph.py`:

- `create_agent(...)`
- `send_message_to_agent(...)`
- `view_agent_graph()`

`send_message_to_agent` injects payload into target agent conversation as a `user` message:

```xml
<message from='PARENT_OR_CHILD'>...</message>
```

### Channel E: Event Bus Telemetry

`maya/telemetry/event_bus.py` emits lifecycle/tool/LLM events to:

- JSONL log (`events.jsonl`)
- UI subscribers

### Channel F: Final persisted outputs

At scan end (`maya/main.py` + `Tracer`):

- `trace.json`
- `findings.json`
- `api_endpoints.json`
- `report.md`
- `report.html`

## 8) Important Root-Orchestration Reality in Current Implementation

Delegation exists, but child-to-root aggregation is mostly cooperative, not automatic:

- children are spawned as async tasks via `AgentGraph.create_agent()`
- no explicit "await child completion and merge result" tool currently exists
- parent must use shared context and/or inter-agent messages for synchronization

Also:

- findings are stored in each agent state
- there is no automatic global reducer that merges all child findings into root state during runtime

## 9) Test and CI Reality (Current Snapshot)

### 9.1 What tests exist

`tests/` currently contains:

- `tests/test_placeholder.py` -> single `assert True`

So functional runtime/tool/agent behavior is not exercised by real unit/integration tests in this snapshot.

### 9.2 What CI runs

`.github/workflows/ci.yml` runs:

- ruff lint/format checks
- `pytest -q -k "not integration"` across Python 3.10/3.11/3.12
- Docker build check on PRs

Given the current tests directory, pytest currently validates only placeholder pass-through behavior.

## 10) External Tools and Dependencies Used by Maya

From Python tool modules + container setup:

- ADB, Frida, Objection
- apktool, JADX, class-dump, strings
- semgrep, nuclei
- MobSF HTTP API
- Caido CLI/API
- curl, ssh, tar, Java signer (uber-apk-signer)

LLM stack:

- LiteLLM abstraction in `maya/llm/llm.py`
- provider configs from env/config file/CLI override

## 11) Data Contracts and Return Pattern

All tools are expected to return `dict` (not raise) with either:

- success-like payload (`status`, `stdout`, `data`, etc.)
- or error payload (`error`, optional metadata)

This enables autonomous recovery:

- tool error text is fed back into LLM context
- agent can re-plan without crashing loop

## 12) Practical Read Path for Another Agent

If another agent needs to reason accurately about this codebase quickly, read in this order:

1. `maya/main.py`
2. `maya/agents/base_agent.py`
3. `maya/agents/maya_agent.py`
4. `maya/tools/registry.py` + `maya/tools/executor.py`
5. `maya/runtime/docker_runtime.py` + `maya/runtime/tool_server.py`
6. `maya/tools/reporting.py`, `shared_context.py`, `agents_graph.py`
7. `companion_app/android/.../Application.kt` + `CommandRouter.kt`
8. `maya/telemetry/event_bus.py` + `tracer.py`
9. `.github/workflows/ci.yml` + `tests/test_placeholder.py`

---

This model describes observed implementation behavior in the current repository state, including mismatches between intended architecture and present runtime/testing coverage.
