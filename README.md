# Maya - మాయ

**Autonomous AI-Powered Mobile Security Agent**

[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Android%20%7C%20iOS-lightgrey?logo=android)](https://developer.android.com/)
[![LiteLLM](https://img.shields.io/badge/LLM-LiteLLM-blueviolet?logo=openai&logoColor=white)](https://github.com/BerriAI/litellm)
[![Docker](https://img.shields.io/badge/sandbox-Docker-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Frida](https://img.shields.io/badge/instrumentation-Frida-orange)](https://frida.re/)

Maya is an autonomous agent for Android and iOS security testing. Point it at an APK or IPA, give it an LLM key, and it runs static analysis, dynamic instrumentation, API discovery, and exploit chaining on its own.

> Active development. See the [Roadmap](docs/ROADMAP.md) for planned features.

---

## Requirements

- Python 3.10+
- Docker Desktop (optional - needed for sandbox mode)
- An LLM API key (OpenAI, Anthropic, Google, or local)
- A rooted Android device or jailbroken iOS device (for dynamic testing)

---

## Install

```bash
git clone https://github.com/USER/MOBSEC.git
cd MOBSEC
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

---

## Configure your LLM

Set an environment variable for your provider:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GEMINI_API_KEY="..."

# Local model (Ollama)
export MAYA_LLM="ollama/llama3"
export LLM_API_BASE="http://localhost:11434"
```

Or create `~/.maya/config.json`:

```json
{
  "model": "openai/gpt-4o",
  "api_key": "sk-...",
  "temperature": 0.2,
  "max_tokens": 8192
}
```

Supported providers:

| Provider | Model string | Env var |
|----------|-------------|---------|
| OpenAI | `openai/gpt-4o` | `OPENAI_API_KEY` |
| Anthropic | `anthropic/claude-sonnet-4-20250514` | `ANTHROPIC_API_KEY` |
| Google | `gemini/gemini-2.0-flash` | `GEMINI_API_KEY` |
| Ollama | `ollama/llama3` | `LLM_API_BASE=http://localhost:11434` |
| LM Studio | `openai/local-model` | `LLM_API_BASE=http://localhost:1234/v1` |
| OpenRouter | `openrouter/anthropic/claude-3.5-sonnet` | `OPENROUTER_API_KEY` |
| Azure | `azure/gpt-4o` | `AZURE_API_KEY` + `AZURE_API_BASE` |

> Full guide: [docs/llm-configuration.md](docs/llm-configuration.md)

---

## Prepare your device

```bash
# Sets up ADB, port forwarding, and frida-server
./scripts/setup-host.sh
```

---

## Run a scan

```bash
# Android - comprehensive scan
maya --target com.example.app --package app.apk --device DEVICE_SERIAL

# iOS
maya --target com.example.app --package app.ipa --device UDID

# Quick surface scan
maya --target com.example.app --package app.apk --device SERIAL --scan-mode quick

# Headless / CI mode (no interactive prompts)
maya --target com.example.app --package app.apk -n

# Pass a specific LLM from the command line
maya --target com.example.app --package app.apk --model anthropic/claude-sonnet-4-20250514 --api-key sk-ant-...
```

### Scan modes

| Mode | What it does |
|------|-------------|
| `quick` | Static analysis only - fast triage |
| `standard` | Static + basic dynamic testing |
| `comprehensive` | Full static, dynamic, API, and exploit chaining (default) |

### Resume a crashed scan

```bash
maya --target com.example.app --resume com.example.app
```

---

## Results

Reports are written to `maya_runs/<target>/`:

```
maya_runs/com.example.app/
├── report.json     # machine-readable findings
├── report.md       # human-readable summary
├── report.html     # styled HTML report
└── events.jsonl    # full telemetry stream
```

---

## CLI Reference

```
maya --help

Core:
  --target TEXT              Package name [required]
  --package PATH             Path to APK or IPA
  --device TEXT              Device serial (ADB serial / iOS UDID)
  --platform [android|ios]   Override platform detection
  -n, --non-interactive      Headless mode
  --model TEXT               LiteLLM model string
  --api-key TEXT             LLM API key
  --scan-mode TEXT           quick / standard / comprehensive

Advanced:
  --instruction TEXT         Inline instruction for the agent
  --instruction-file PATH    Load instructions from file
  --output-dir PATH          Override output directory
  --max-agents INT           Max parallel sub-agents (default: 7)
  --resume TEXT              Resume from checkpoint
  --skills TEXT              Comma-separated skill names to load
  --skills-dir PATH          Custom skills directory
  --list-skills              List available skills and exit
```

---

## Skills

Skills are Markdown files that tell agents what to look for and how to use tools. Load them with `--skills`:

```bash
maya --list-skills
maya --target com.app --package app.apk --skills ssl_pinning_bypass,flutter_analysis
```

Built-in skill categories: `vulnerabilities/`, `tools/`, `frameworks/`, `platforms/`, `agents/`, `coordination/`, `scan_modes/`.

---

## Docker

Run without installing anything locally:

```bash
docker pull ghcr.io/USER/maya-agent:latest

docker run --rm -it \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -v /path/to/app.apk:/data/app.apk \
  ghcr.io/USER/maya-agent:latest \
  --target com.example.app --package /data/app.apk -n
```

Build locally:

```bash
docker build -f containers/Dockerfile.sandbox -t maya-agent:latest .
```

> Full guide: [docs/building-and-infrastructure.md](docs/building-and-infrastructure.md)

---

## Development

```bash
pip install -e ".[dev]"

pytest -q -k "not integration"   # unit tests
pytest -q -m integration          # device-required tests
ruff check . && ruff format --check .
```

---

## Documentation

| Guide | |
|-------|-|
| [LLM Configuration](docs/llm-configuration.md) | All provider options |
| [Companion App](docs/companion-app.md) | Android/iOS on-device setup |
| [Building & Infrastructure](docs/building-and-infrastructure.md) | Docker and host setup |
| [Roadmap](docs/ROADMAP.md) | Planned features |
| [Contributing](docs/contributing.md) | How to contribute |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Tools return `dict`, never raise, use `@register_tool`.

## License

MIT - see [LICENSE](LICENSE).
