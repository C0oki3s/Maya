# Maya

**Autonomous AI-Powered Mobile Security Agent for Android & iOS**

[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

Autonomous security testing agent for mobile apps. Point it at an APK/IPA, provide an LLM API key, and it runs static analysis, dynamic instrumentation, and exploit chaining automatically.

## Quick Start

### Option 1: Docker (Easiest - No Setup)

```bash
docker run --rm -it \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -v /path/to/app.apk:/data/app.apk \
  ghcr.io/C0oki3s/maya-agent:latest \
  --target com.example.app --package /data/app.apk -n
```

Replace `OPENAI_API_KEY` with your key or use `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, etc.

### Option 2: Local Installation

```bash
git clone https://github.com/C0oki3s/Maya.git && cd Maya
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

export OPENAI_API_KEY="sk-..."
maya --target com.example.app --package app.apk --device SERIAL
```

**iOS:**
```bash
maya --target com.example.app --package app.ipa --device UDID
```

## Usage

```bash
maya --target PACKAGE_NAME --package PATH_TO_APK_OR_IPA [--device SERIAL] [OPTIONS]
```

### Common Options

| Flag | Purpose |
|------|---------|
| `--target` | Package name (required) |
| `--package` | Path to APK or IPA (required) |
| `--device` | Device serial / iOS UDID |
| `--scan-mode quick\|standard\|comprehensive` | Analysis depth (default: comprehensive) |
| `-n, --non-interactive` | Headless mode |
| `--model` | LLM: `openai/gpt-4o`, `anthropic/claude-sonnet-4-20250514`, etc. |
| `--api-key` | LLM API key (override env var) |

### Examples

```bash
# Quick static analysis
maya --target com.app --package app.apk --scan-mode quick

# Full scan with custom LLM
maya --target com.app --package app.apk --model anthropic/claude-sonnet-4-20250514 --api-key sk-ant-...

# Resume interrupted scan
maya --target com.app --resume com.app
```

## LLM Configuration

### Environment Variables

Set any of these to configure your LLM:

```bash
# Model and API key
export MAYA_LLM="gpt-4o"                    # Model string (required)
export LLM_API_KEY="sk-..."                 # API key for the provider
export LLM_API_BASE="http://localhost:1234/v1"  # API base URL (optional, for self-hosted)
export MAYA_REASONING_EFFORT="high"         # Optional: high/medium/low
```

### Supported Providers

Maya uses **LiteLLM**, which supports **100+ LLM providers** (OpenAI, Anthropic, Google, Groq, Ollama, LM Studio, Azure, and more).

See [LiteLLM supported models](https://docs.litellm.ai/docs/providers) for the complete list and model strings.

### Config File

Or create `~/.maya/config.json`:

```json
{
  "model": "gpt-4o",
  "api_key": "sk-...",
  "api_base": "http://localhost:1234/v1",
  "temperature": 0.1,
  "max_tokens": 8192,
  "reasoning_effort": "high"
}
```

### Priority Order

1. **CLI flags** (highest): `--model gpt-4o --api-key sk-...`
2. **Environment variables**: `export MAYA_LLM="gpt-4o"`
3. **Config file** `~/.maya/config.json` (lowest)

## Results

Reports saved to `maya_runs/<package_name>/`:

```
report.json       # Machine-readable findings
report.md         # Human-readable summary
report.html       # Styled HTML report
events.jsonl      # Full telemetry stream
```

## Development

```bash
pip install -e ".[dev]"
pytest -q -k "not integration"    # Unit tests
ruff check . && ruff format .     # Lint & format
```

## Documentation

- [LLM Configuration](docs/llm-configuration.md) — All provider options
- [Building & Infrastructure](docs/building-and-infrastructure.md) — Docker & host setup
- [Roadmap](docs/ROADMAP.md) — Planned features
- [Contributing](CONTRIBUTING.md) — How to contribute

## License

MIT
