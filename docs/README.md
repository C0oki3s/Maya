<p align="center">
  <h1 align="center">Maya</h1>
  <p align="center"><strong>Autonomous AI-Powered Mobile Security Agent</strong></p>
  <p align="center">
    <a href="https://github.com/USER/MOBSEC/actions/workflows/ci.yml"><img src="https://github.com/USER/MOBSEC/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
    <a href="https://github.com/USER/MOBSEC/actions/workflows/docker-publish.yml"><img src="https://github.com/USER/MOBSEC/actions/workflows/docker-publish.yml/badge.svg" alt="Docker"></a>
    <a href="https://github.com/USER/MOBSEC/pkgs/container/maya-agent"><img src="https://img.shields.io/badge/ghcr.io-maya--agent-blue?logo=docker" alt="GHCR"></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-green" alt="License"></a>
  </p>
</p>

---

Maya is an autonomous mobile application security testing agent that combines LLM reasoning with a rich toolkit of security instruments. It uses a **Think → Plan → Act → Observe** cognitive loop to run comprehensive Android and iOS security assessments — static analysis, dynamic testing, API discovery, and exploit chaining — with minimal human intervention.

> **Status** — Active development. See the [Roadmap](docs/ROADMAP.md) for planned features.

---

## Table of Contents

- [Key Features](#key-features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
- [LLM Configuration](#llm-configuration)
- [Skills System](#skills-system)
- [Companion App](#companion-app)
- [Docker](#docker)
- [Frida Scripts](#frida-scripts)
- [Development](#development)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Key Features

| Feature | Description |
|---------|-------------|
| **Multi-Agent Architecture** | Root orchestrator spawns specialized sub-agents (static, dynamic, API, exploit) on a strict tree graph |
| **40+ Security Tools** | Frida, Objection, APKTool, JADX, MobSF, Caido, Nuclei, Semgrep, Reflutter — all as `@register_tool` functions |
| **Skill System** | Community-extensible Markdown knowledge packs injected into agent prompts |
| **Docker Sandbox** | Every agent gets its own Kali-based container. Dangerous ops never touch the host |
| **Any LLM** | [LiteLLM](https://github.com/BerriAI/litellm) — OpenAI, Anthropic, Google, Ollama, Azure, local models, any OpenAI-compatible endpoint |
| **Companion App** | On-device Android (Ktor HTTP) / iOS (Swift) service for runtime testing |
| **Checkpoint & Resume** | Crash-resilient — resume from the last saved state |
| **Reporting** | JSON, Markdown, and HTML reports with severity ratings, PoC steps, and remediation |
| **23 Frida Scripts** | Pre-built scripts for bypass, enumeration, exploitation, and data extraction |

---

## Architecture

```
CLI (click) → ScanConfig → Root MayaAgent
  ├── Sub-Agent (Static Analysis)      ← spawned via create_agent tool
  ├── Sub-Agent (Dynamic Testing)
  ├── Sub-Agent (API Discovery)
  └── Sub-Agent (Platform-specific)
       Each agent runs: Think → Plan → Act → Observe loop
       Each agent gets: own Docker sandbox + tool_server (FastAPI)
       All actions go through: @register_tool → XML schema → executor
```

| Layer | Location | Purpose |
|-------|----------|---------|
| CLI | `maya/main.py` | Parse args, build `ScanConfig`, launch root agent |
| Agents | `maya/agents/` | Agent loop, tree graph, state, checkpointing |
| Tools | `maya/tools/` | 17 tool modules — registration, validation, routing, sandbox execution |
| LLM | `maya/llm/` | LiteLLM wrapper, config, memory compression, token tracking |
| Runtime | `maya/runtime/` | Docker sandbox lifecycle, in-container FastAPI tool server |
| Skills | `maya/skills/` | 7 categories of Markdown knowledge packs |
| Telemetry | `maya/telemetry/` | JSON/MD/HTML report generation |

> Deep-dive: [docs/01-ARCHITECTURE.md](docs/01-ARCHITECTURE.md)

---

## Quick Start

### Prerequisites

- **Python 3.10+**
- **Docker Desktop** (for sandbox execution; optional — Maya runs in dry-run mode without it)
- **An LLM API key** (OpenAI, Anthropic, Google, or a local model)
- **A connected device or emulator** (for dynamic testing)

### 1. Install

```bash
git clone https://github.com/USER/MOBSEC.git
cd MOBSEC
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Or use the install script:

```bash
./scripts/install.sh
```

### 2. Configure your LLM

Set one environment variable for your provider:

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Google Gemini
export GEMINI_API_KEY="..."

# Local model (Ollama, LM Studio, etc.)
export MAYA_LLM="ollama/llama3"
export LLM_API_BASE="http://localhost:11434"
```

Or write `~/.maya/config.json`:

```json
{
  "model": "openai/gpt-4o",
  "api_key": "sk-...",
  "temperature": 0.2,
  "max_tokens": 8192
}
```

> Full guide: [docs/llm-configuration.md](docs/llm-configuration.md)

### 3. Prepare your device

```bash
# Start ADB, forward ports, launch frida-server
./scripts/setup-host.sh
```

### 4. Run a scan

```bash
# Android — full comprehensive scan
maya --target com.example.app --package app.apk --device DEVICE_SERIAL

# iOS
maya --target com.example.app --package app.ipa --device UDID

# Quick scan
maya --target com.example.app --package app.apk --device SERIAL --scan-mode quick

# Headless / CI mode
maya --target com.example.app --package app.apk -n
```

### 5. View results

Reports are written to `maya_runs/<target>/`:

```
maya_runs/com.example.app/
├── report.json        # Machine-readable findings
├── report.md          # Human-readable Markdown
├── report.html        # Styled HTML report
└── events.jsonl       # Full telemetry stream
```

---

## Usage Guide

### CLI Reference

```
maya --help

Core options:
  --target TEXT              Target package name (e.g. com.app.example) [required]
  --package PATH             Path to APK or IPA file
  --device TEXT              Device serial (adb serial / iOS UDID)
  --platform [android|ios]   Override auto-detected platform
  --task TEXT                Override auto-generated task description
  -n, --non-interactive      Force headless mode
  --model TEXT               LiteLLM model string (e.g. openai/gpt-4o)
  --api-key TEXT             LLM API key
```

<details>
<summary><strong>Advanced options</strong></summary>

```
  --scan-mode [quick|standard|comprehensive]   Scan depth (default: comprehensive)
  --instruction TEXT           Inline instruction for the agent
  --instruction-file PATH      Load instructions from a file
  --output-dir PATH            Override output directory
  --max-agents INT             Max concurrent sub-agents (default: 7)
  --resume TEXT                Resume from a previous checkpoint
  --skills-dir PATH            Custom skills directory
  --skills TEXT                Comma-separated skill names to load
  --default-skills TEXT        Default skills always loaded
  --agent-skill TEXT           Per-agent skill (repeatable)
  --list-skills                List all available skills and exit
  --role [root|static|dynamic|api|exploit]   Agent role
```

</details>

### Scan Modes

| Mode | Depth | Use case |
|------|-------|----------|
| `quick` | Surface-level static analysis | CI gates, quick triage |
| `standard` | Static + basic dynamic | Regular assessments |
| `comprehensive` | Full static + dynamic + API + exploit chaining | Penetration tests |

### Resume a Crashed Scan

```bash
maya --target com.example.app --resume com.example.app
```

Maya picks up from the last checkpoint — no repeated work.

---

## LLM Configuration

Maya uses [LiteLLM](https://docs.litellm.ai/) under the hood, which means **any LLM provider works**:

| Provider | Model string | Env var |
|----------|-------------|---------|
| OpenAI | `openai/gpt-4o`, `openai/gpt-4o-mini` | `OPENAI_API_KEY` |
| Anthropic | `anthropic/claude-sonnet-4-20250514`, `anthropic/claude-3.5-sonnet` | `ANTHROPIC_API_KEY` |
| Google | `gemini/gemini-2.0-flash` | `GEMINI_API_KEY` |
| Azure OpenAI | `azure/gpt-4o` | `AZURE_API_KEY` + `AZURE_API_BASE` |
| AWS Bedrock | `bedrock/anthropic.claude-3-sonnet` | AWS credentials |
| Ollama (local) | `ollama/llama3`, `ollama/codestral` | `LLM_API_BASE=http://localhost:11434` |
| LM Studio | `openai/local-model` | `LLM_API_BASE=http://localhost:1234/v1` |
| Together AI | `together_ai/meta-llama/Llama-3-70b` | `TOGETHERAI_API_KEY` |
| OpenRouter | `openrouter/anthropic/claude-3.5-sonnet` | `OPENROUTER_API_KEY` |

**Config precedence**: `--model` / `--api-key` CLI flags > environment variables (`MAYA_LLM`, `LLM_API_KEY`, `LLM_API_BASE`) > `~/.maya/config.json` > defaults.

```bash
# Use Claude from the CLI
maya --target com.app --model anthropic/claude-sonnet-4-20250514 --api-key sk-ant-...

# Use a local Ollama model
MAYA_LLM=ollama/llama3 LLM_API_BASE=http://localhost:11434 maya --target com.app
```

> Full guide: [docs/llm-configuration.md](docs/llm-configuration.md)

---

## Skills System

Skills are Markdown files that teach agents **what to find** and **how to operate tools**. They are injected into the system prompt as `<specialized_knowledge>` blocks.

```
maya/skills/
├── vulnerabilities/     # WHAT to find — insecure_storage, ssl_pinning, auth_bypass, insecure_crypto, api_security
├── tools/               # HOW to use tools — frida_operations, caido_operations, objection_operations
├── frameworks/          # App frameworks — flutter_analysis, react_native, xamarin
├── platforms/           # Platform internals — android_internals, ios_internals
├── agents/              # Agent behavior — root_orchestrator, static_analyzer, dynamic_tester
├── coordination/        # Multi-agent — delegation_strategy, context_sharing
└── scan_modes/          # Scan depth configuration
```

**Loading precedence**: `--skills-dir` > `$MAYA_SKILLS_DIR` > `~/.maya/skills/` > built-in defaults.

Skills support **dependency auto-loading** — loading `ssl_pinning_bypass` automatically pulls in `frida_operations`.

```bash
# List available skills
maya --list-skills

# Load specific skills
maya --target com.app --skills ssl_pinning_bypass,flutter_analysis

# Use a community skill pack
maya --target com.app --skills-dir ~/community-skills/
```

> Full guide: [docs/skills-system.md](docs/05-SKILLS-RUNTIME-COMPANION-APP.md) · [Copact.md](docs/Copact.md)

---

## Companion App

Maya deploys an on-device HTTP companion service for runtime operations that require device-side execution.

| Platform | Tech | Port | Status |
|----------|------|------|--------|
| **Android** | Kotlin / Ktor / Netty | `9999` | 16+ modules, functional |
| **iOS** | Swift | `9999` | Scaffold — 9 commands |

**Android modules**: AppManager, PackageAnalyzer, ActivityInspector, ContentProviderInspector, BroadcastInspector, ServiceInspector, DeviceInfo, VulnerabilityScanner, FridaGadgetInjector, TrafficCapture, FilesystemInspector, LogCollector, ExploitRunner, ScreenshotCapture.

```bash
# Port forwarding (done automatically by setup-host.sh)
adb forward tcp:9999 tcp:9999

# The agent communicates with the companion via device_bridge tools
maya --target com.app --device SERIAL
```

> Full guide: [docs/companion-app.md](docs/companion-app.md)

---

## Docker

### Pull from GitHub Container Registry

```bash
docker pull ghcr.io/USER/maya-agent:latest
```

### Build locally

```bash
docker build -f containers/Dockerfile.sandbox -t maya-agent:latest .
```

### Run

```bash
docker run --rm -it \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -v /path/to/app.apk:/data/app.apk \
  ghcr.io/USER/maya-agent:latest \
  --target com.example.app --package /data/app.apk -n
```

The sandbox image is based on **Kali Linux** and bundles: Python 3, Node.js, Go, Java (JDK), ADB, nmap, APKTool, JADX, dex2jar, SQLMap, Binwalk, ffuf, Frida, Objection, MITMProxy, Semgrep, Nuclei, httpx, Caido, Reflutter, and more.

> Full guide: [docs/building-and-infrastructure.md](docs/building-and-infrastructure.md)

---

## Frida Scripts

Maya ships with **23 pre-built Frida scripts** organized by purpose:

```
assets/frida-scripts/
├── bypass/           # root_detection, ssl_pinning, integrity_check, emulator_detection, debug_detection
├── enumerate/        # loaded_classes, class_methods, native_exports, intent_monitor, rasp_detection
├── exploit/          # webview_rce, deeplink_injection, content_provider_dump
├── extract/          # crypto_keys, shared_preferences, sqlite_queries, network_requests, tls_version_check
└── ios/              # nsurlsession_hook, data_protection
```

The agent selects scripts automatically based on the scan context, or you can reference them in custom instructions.

---

## Development

```bash
# Install with dev extras
pip install -e ".[dev]"

# Run all tests (except device-gated)
pytest -q -k "not integration"

# Run integration tests (needs connected device)
pytest -q -m integration

# Lint
pip install ruff
ruff check .
ruff format --check .
```

**29 tests** across agent loop, tool registry, LLM config, parser, compliance, companion commands, Docker runtime, skills loader, and smoke tests.

---

## Project Structure

```
maya/
├── main.py              # CLI entrypoint (click)
├── models.py            # ScanConfig, core models
├── agents/              # BaseAgent, MayaAgent, graph, state, checkpointing
├── llm/                 # LLMClient, LLMConfig, memory compressor, token tracker
├── runtime/             # DockerRuntime, FastAPI tool_server
├── skills/              # 7 skill categories (Markdown knowledge packs)
│   ├── vulnerabilities/ # insecure_storage, ssl_pinning_bypass, auth_bypass, insecure_crypto, api_security
│   ├── tools/           # frida_operations, caido_operations, objection_operations, apktool_operations
│   ├── frameworks/      # flutter_analysis, react_native_analysis, xamarin_analysis
│   ├── platforms/       # android_internals, ios_internals
│   ├── agents/          # root_orchestrator, static_analyzer, dynamic_tester
│   ├── coordination/    # delegation_strategy, context_sharing
│   └── scan_modes/      # quick, standard, comprehensive
├── tools/               # 17 tool modules (40+ @register_tool functions)
├── telemetry/           # Tracer, event bus, report generation
└── ui/                  # TUI components
containers/
└── Dockerfile.sandbox   # Kali-based sandbox image
companion_app/
├── android/             # Kotlin/Ktor companion server (16+ modules)
└── ios/                 # Swift companion scaffold (9 commands)
assets/
├── frida-scripts/       # 23 pre-built Frida scripts
├── signer/              # APK/IPA signing helpers
└── wordlists/           # deeplink-payloads.txt, sqli-payloads.txt
docs/                    # Full documentation
tests/                   # 29 test files
scripts/
├── install.sh           # Bootstrap script
└── setup-host.sh        # ADB + port forwarding setup
```

---

## Documentation

Full documentation lives in [`docs/`](docs/INDEX.md):

| Guide | Description |
|-------|-------------|
| [LLM Configuration](docs/llm-configuration.md) | Using any model provider with Maya |
| [Companion App](docs/companion-app.md) | Android & iOS on-device companion setup |
| [Building & Infrastructure](docs/building-and-infrastructure.md) | Docker, sandbox, host setup |
| [Contributing](docs/contributing.md) | How to contribute tools, skills, and improvements |
| [Roadmap](docs/ROADMAP.md) | Planned features and future direction |

**Specification documents:**

| Doc | Topic |
|-----|-------|
| [01-ARCHITECTURE](docs/01-ARCHITECTURE.md) | System design, agent graph |
| [02-MODELS](docs/02-MODELS-AND-DATA-STRUCTURES.md) | Core data models |
| [03-TOOLS](docs/03-TOOLS-IMPLEMENTATION-GUIDE.md) | Tool system deep-dive |
| [04-AGENTS & LLM](docs/04-AGENT-SYSTEM-AND-LLM-INTEGRATION.md) | Agent loop, LLM integration |
| [05-SKILLS & RUNTIME](docs/05-SKILLS-RUNTIME-COMPANION-APP.md) | Skills, runtime, companion |
| [06-STRIX REFERENCE](docs/06-STRIX-REVERSE-ENGINEERING-REFERENCE.md) | Reference architecture |
| [07-ROADMAP](docs/07-IMPLEMENTATION-ROADMAP.md) | Implementation roadmap |
| [08-AMENDMENTS](docs/08-AMENDMENTS-AND-LIMITATION-FIXES.md) | Design fixes |

---

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for the full plan. Highlights:

- **iOS Companion** — Complete the jailbreak-side Swift companion with full module parity
- **Whitebox Testing** — Source code analysis mode with code-aware agent skills
- **CI/CD Integration** — GitHub Actions / GitLab CI pipeline templates for automated scanning
- **Emulator Support** — First-class Android emulator (AVD) and iOS Simulator support
- **Dynamic Frida Scripts** — AI-generated scripts, Frida CodeShare integration, runtime script selection
- **Skill Improvements** — Community skill marketplace, versioned skill packs, auto-updating
- **MobSF Deep Integration** — Tighter coupling with MobSF for static analysis correlation

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for:

- Development environment setup
- Code conventions (tools return `dict`, never raise, use `@register_tool`)
- How to add new tools, skills, and Frida scripts
- PR review process (1 approval + passing CI + CodeQL)
- Skill authoring guide

**Quick links**: [Bug Report](https://github.com/USER/MOBSEC/issues/new?template=bug_report.md) · [Feature Request](https://github.com/USER/MOBSEC/issues/new?template=feature_request.md) · [Discussions](https://github.com/USER/MOBSEC/discussions)

---

## Security

If you discover a vulnerability, please report it responsibly. See [SECURITY.md](.github/SECURITY.md).

## License

MIT — see [LICENSE](LICENSE).
