from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from typing import Any, Protocol

from .config import LLMConfig
from .token_tracker import get_token_tracker

try:
    import litellm
    from litellm.exceptions import (
        AuthenticationError,
        RateLimitError,
        PermissionDeniedError,
        APIError,
        BadRequestError,
    )
except Exception:  # noqa: BLE001
    litellm = None
    AuthenticationError = Exception
    RateLimitError = Exception
    PermissionDeniedError = Exception
    APIError = Exception
    BadRequestError = Exception


@dataclass(slots=True)
class LLMResponse:
    content: str | None
    tool_calls: list[dict] | None = None
    usage: dict | None = None
    model: str | None = None
    finish_reason: str | None = None


class LLMProtocol(Protocol):
    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse: ...


class LLMClient:
    """LiteLLM wrapper with deterministic fallback for local tests."""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig.load()

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        if self.config.model.startswith("mock/"):
            return self._fallback_response()

        if litellm is None:
            return self._fallback_response("LiteLLM is not installed; using fallback response")

        temp = self.config.temperature if temperature is None else temperature
        token_limit = self.config.max_tokens if max_tokens is None else max_tokens

        if self.config.api_key:
            litellm.api_key = self.config.api_key
        if self.config.api_base:
            litellm.api_base = self.config.api_base

        delay = 5
        for attempt in range(self.config.max_retries + 1):
            try:
                response: Any = await litellm.acompletion(
                    model=self.config.model,
                    messages=messages,
                    temperature=temp,
                    max_tokens=token_limit,
                    drop_params=True,
                )
                message = response.choices[0].message
                usage = getattr(response, "usage", None)
                usage_dict = dict(usage) if usage is not None else {}
                resp = LLMResponse(
                    content=getattr(message, "content", ""),
                    tool_calls=getattr(message, "tool_calls", []),
                    usage=usage_dict,
                    model=getattr(response, "model", self.config.model),
                    finish_reason=getattr(response.choices[0], "finish_reason", "stop"),
                )
                # Record token usage and cost
                await get_token_tracker().record(usage_dict, model=resp.model or self.config.model)
                return resp
            except AuthenticationError as exc:
                # 401 - Invalid API key
                provider = self.config.model.split("/")[0] if "/" in self.config.model else "unknown"
                provider_upper = provider.upper()
                print(f"\n[FATAL] Invalid API key for {self.config.model}", file=sys.stderr, flush=True)
                print(f"  Error: {exc}", file=sys.stderr, flush=True)
                print(f"  Please check your API key configuration:", file=sys.stderr, flush=True)
                print(f"    - Set {provider_upper}_API_KEY environment variable", file=sys.stderr, flush=True)
                print(f"    - Or create ~/.maya/config.json with valid credentials", file=sys.stderr, flush=True)
                print(f"  Supported providers: OpenAI, Anthropic, Google, Azure, Vertex AI, Ollama, etc.", file=sys.stderr, flush=True)
                sys.exit(1)
            except PermissionDeniedError as exc:
                # 403 - No access to model
                provider = self.config.model.split("/")[0] if "/" in self.config.model else "unknown"
                print(f"\n[FATAL] Permission denied for model '{self.config.model}'", file=sys.stderr, flush=True)
                print(f"  Error: {exc}", file=sys.stderr, flush=True)
                print(f"  Your API key does not have access to this model.", file=sys.stderr, flush=True)
                print(f"  Try a different {provider} model or check your plan/subscription.", file=sys.stderr, flush=True)
                sys.exit(1)
            except RateLimitError as exc:
                # 429 - Rate limit hit
                if attempt >= self.config.max_retries:
                    print(f"\n[FATAL] Rate limit exceeded for {self.config.model}", file=sys.stderr, flush=True)
                    print(f"  Error: {exc}", file=sys.stderr, flush=True)
                    print(f"  You've hit your API rate limit. Try again later.", file=sys.stderr, flush=True)
                    sys.exit(1)
                wait_time = delay * (2 ** attempt)
                print(f"  [WARN] Rate limit hit, retrying in {wait_time}s... (attempt {attempt + 1}/{self.config.max_retries + 1})", file=sys.stderr, flush=True)
                await asyncio.sleep(wait_time)
                continue
            except BadRequestError as exc:
                # 400 - Invalid request (bad model name, invalid params)
                provider = self.config.model.split("/")[0] if "/" in self.config.model else "unknown"
                print(f"\n[FATAL] Bad request to {self.config.model}", file=sys.stderr, flush=True)
                print(f"  Error: {exc}", file=sys.stderr, flush=True)
                print(f"  Check that your model name is correct.", file=sys.stderr, flush=True)
                print(f"  Format: provider/model-name (e.g., {provider}/model-name)", file=sys.stderr, flush=True)
                print(f"  Examples: openai/gpt-4o-mini, anthropic/claude-sonnet-4, google/gemini-1.5-pro", file=sys.stderr, flush=True)
                sys.exit(1)
            except APIError as exc:
                # 5xx - Server error
                if attempt >= self.config.max_retries:
                    print(f"\n[FATAL] API error from {self.config.model}", file=sys.stderr, flush=True)
                    print(f"  Error: {exc}", file=sys.stderr, flush=True)
                    print(f"  The LLM provider is having issues. Try again later.", file=sys.stderr, flush=True)
                    sys.exit(1)
                print(f"  [WARN] API error, retrying in {delay}s... (attempt {attempt + 1}/{self.config.max_retries + 1})", file=sys.stderr, flush=True)
                await asyncio.sleep(delay)
                delay *= 2
                continue
            except Exception as exc:  # noqa: BLE001
                # Unknown error
                if attempt >= self.config.max_retries:
                    print(f"\n[FATAL] Unexpected LLM error: {exc}", file=sys.stderr, flush=True)
                    print(f"  Model: {self.config.model}", file=sys.stderr, flush=True)
                    print(f"  This might be a network issue or unsupported model.", file=sys.stderr, flush=True)
                    return self._fallback_response(f"LiteLLM failure: {exc}")
                await asyncio.sleep(delay)
                delay *= 2

        return self._fallback_response()

    def _fallback_response(self, note: str | None = None) -> LLMResponse:
        content = "<function=agent_finish><parameter=report>Fallback completion"
        if note:
            content += f" ({note})"
        content += "</parameter></function>"
        return LLMResponse(
            content=content,
            tool_calls=[],
            usage={"prompt_tokens": 0, "completion_tokens": 0},
            model=self.config.model,
            finish_reason="stop",
        )

    async def validate(self) -> bool:
        """Quick validation check to ensure API key and model are working.
        
        Returns True if valid, exits with error message if invalid.
        """
        if self.config.model.startswith("mock/"):
            return True
        
        if litellm is None:
            print("\n[WARN] LiteLLM not installed, skipping validation", file=sys.stderr, flush=True)
            return True
        
        print(f"  Validating LLM connection ({self.config.model})...", file=sys.stderr, flush=True)
        
        try:
            # Quick test with minimal tokens
            response = await self.generate(
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
            )
            if response.content:
                print(f"LLM connection valid", file=sys.stderr, flush=True)
                return True
            return False
        except Exception:
            # Errors are already handled and printed in generate()
            return False
