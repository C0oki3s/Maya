# LLM Configuration

Maya uses [LiteLLM](https://docs.litellm.ai/) as its LLM abstraction layer, which means it works with **100+ LLM providers** out of the box — cloud APIs, local models, and self-hosted endpoints.

---

## Quick Setup

Set one environment variable and go:

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."
maya --target com.app --package app.apk --device SERIAL

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."
maya --target com.app --model anthropic/claude-sonnet-4-20250514

# Local Ollama
export MAYA_LLM="ollama/llama3"
export LLM_API_BASE="http://localhost:11434"
maya --target com.app
```

---

## Configuration Precedence

Maya resolves LLM settings in this order (highest priority first):

1. **CLI flags**: `--model`, `--api-key`
2. **Environment variables**: `MAYA_LLM`, `LLM_API_KEY`, `LLM_API_BASE`, `MAYA_REASONING_EFFORT`
3. **Config file**: `~/.maya/config.json`
4. **Defaults**: `mock/local` model (for testing without an API key)

---

## Config File

Create `~/.maya/config.json`:

```json
{
  "model": "openai/gpt-4o",
  "api_key": "sk-...",
  "api_base": null,
  "temperature": 0.2,
  "max_tokens": 8192,
  "max_retries": 3,
  "reasoning_effort": null,
  "verbose": false
}
```

| Field | Default | Description |
|-------|---------|-------------|
| `model` | `mock/local` | LiteLLM model string (see provider table below) |
| `api_key` | `null` | API key for the provider |
| `api_base` | `null` | Custom API base URL (for local models or proxies) |
| `temperature` | `0.1` | Lower = more deterministic. `0.1`–`0.2` recommended for security analysis |
| `max_tokens` | `8192` | Maximum tokens in LLM response |
| `max_retries` | `3` | Retry count on failure (exponential backoff) |
| `reasoning_effort` | `null` | Provider-specific reasoning effort parameter |
| `verbose` | `false` | Print raw LLM requests/responses |

---

## Environment Variables

| Variable | Maps to | Example |
|----------|---------|---------|
| `MAYA_LLM` | `model` | `openai/gpt-4o` |
| `LLM_API_KEY` | `api_key` | `sk-...` |
| `LLM_API_BASE` | `api_base` | `http://localhost:11434` |
| `MAYA_REASONING_EFFORT` | `reasoning_effort` | `high` |
| `OPENAI_API_KEY` | Auto-detected by LiteLLM | `sk-...` |
| `ANTHROPIC_API_KEY` | Auto-detected by LiteLLM | `sk-ant-...` |
| `GEMINI_API_KEY` | Auto-detected by LiteLLM | `AI...` |
| `AZURE_API_KEY` | Auto-detected by LiteLLM | `...` |
| `AZURE_API_BASE` | Auto-detected by LiteLLM | `https://your-resource.openai.azure.com` |

---

## Supported Providers

### Cloud Providers

| Provider | Model String | Required Env Var |
|----------|-------------|------------------|
| **OpenAI** | `openai/gpt-4o` | `OPENAI_API_KEY` |
| | `openai/gpt-4o-mini` | |
| | `openai/gpt-4-turbo` | |
| | `openai/o1-preview` | |
| **Anthropic** | `anthropic/claude-sonnet-4-20250514` | `ANTHROPIC_API_KEY` |
| | `anthropic/claude-3.5-sonnet` | |
| | `anthropic/claude-3-haiku` | |
| **Google** | `gemini/gemini-2.0-flash` | `GEMINI_API_KEY` |
| | `gemini/gemini-1.5-pro` | |
| **Azure OpenAI** | `azure/<deployment-name>` | `AZURE_API_KEY` + `AZURE_API_BASE` |
| **AWS Bedrock** | `bedrock/anthropic.claude-3-sonnet` | AWS credentials |
| | `bedrock/amazon.titan-text-express` | |
| **Together AI** | `together_ai/meta-llama/Llama-3-70b` | `TOGETHERAI_API_KEY` |
| **OpenRouter** | `openrouter/anthropic/claude-3.5-sonnet` | `OPENROUTER_API_KEY` |
| **Groq** | `groq/llama3-70b-8192` | `GROQ_API_KEY` |
| **Fireworks** | `fireworks_ai/accounts/fireworks/models/llama-v3-70b` | `FIREWORKS_API_KEY` |
| **Mistral** | `mistral/mistral-large-latest` | `MISTRAL_API_KEY` |
| **Cohere** | `cohere/command-r-plus` | `COHERE_API_KEY` |
| **Deepseek** | `deepseek/deepseek-chat` | `DEEPSEEK_API_KEY` |

### Local / Self-Hosted

| Setup | Model String | Config |
|-------|-------------|--------|
| **Ollama** | `ollama/llama3`, `ollama/codestral`, `ollama/mistral` | `LLM_API_BASE=http://localhost:11434` |
| **LM Studio** | `openai/local-model` | `LLM_API_BASE=http://localhost:1234/v1` |
| **vLLM** | `openai/<model-name>` | `LLM_API_BASE=http://localhost:8000/v1` |
| **text-generation-inference** | `openai/tgi` | `LLM_API_BASE=http://localhost:8080/v1` |
| **LocalAI** | `openai/<model-name>` | `LLM_API_BASE=http://localhost:8080/v1` |

For any OpenAI-compatible endpoint, use the `openai/` prefix and set `LLM_API_BASE`.

---

## Examples

### OpenAI GPT-4o

```bash
export OPENAI_API_KEY="sk-..."
maya --target com.bank.app --package bank.apk --device emulator-5554
```

### Anthropic Claude (via CLI flag)

```bash
maya --target com.app --model anthropic/claude-sonnet-4-20250514 --api-key sk-ant-...
```

### Local Ollama

```bash
# Start Ollama with a model
ollama pull llama3
ollama serve

# Point Maya at it
export MAYA_LLM="ollama/llama3"
export LLM_API_BASE="http://localhost:11434"
maya --target com.app --package app.apk
```

### Azure OpenAI

```bash
export AZURE_API_KEY="..."
export AZURE_API_BASE="https://your-resource.openai.azure.com"
maya --target com.app --model azure/gpt-4o-deployment
```

### OpenRouter (access multiple providers)

```bash
export OPENROUTER_API_KEY="sk-or-..."
maya --target com.app --model openrouter/anthropic/claude-3.5-sonnet
```

---

## Model Recommendations

| Use Case | Recommended Model | Notes |
|----------|-------------------|-------|
| **Best results** | `anthropic/claude-sonnet-4-20250514` or `openai/gpt-4o` | Best reasoning for security analysis |
| **Cost-effective** | `openai/gpt-4o-mini` or `anthropic/claude-3-haiku` | Good for quick scans |
| **Privacy-first** | `ollama/llama3` or `ollama/codestral` | All data stays local |
| **Enterprise** | `azure/gpt-4o` or `bedrock/anthropic.claude-3-sonnet` | Compliance and data residency |
| **Budget** | `groq/llama3-70b-8192` or `together_ai/meta-llama/Llama-3-70b` | Fast and cheap |

### Temperature Settings

- `0.1` — Deterministic, consistent results (default, recommended)
- `0.2` — Slight variation, good for creative exploit thinking
- `0.5+` — Not recommended for security analysis (too random)

---

## Mock Mode

When no API key is configured, Maya runs with `mock/local` model. This returns deterministic responses and is used for:

- Running tests without API costs
- Validating the agent loop and tool execution
- CI/CD pipeline testing

```bash
# Explicit mock mode
maya --target com.app --model mock/local
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `AuthenticationError` | Check your API key is set correctly |
| `RateLimitError` | Maya retries automatically (3x with backoff). Lower `--max-agents` to reduce parallel requests |
| `Connection refused` (local model) | Verify `LLM_API_BASE` URL and that the model server is running |
| Responses are too short | Increase `max_tokens` in config |
| Model not found | Check the model string format matches [LiteLLM docs](https://docs.litellm.ai/docs/providers) |
| Slow responses | Consider a faster provider or reduce `--scan-mode` to `quick` |
