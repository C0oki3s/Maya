from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from time import time
from typing import Any

# ── Per-1M-token pricing (USD) ──────────────────────────────────────
# Source: provider pricing pages as of 2026-03.
# Keys are LiteLLM model strings; regex-matched with startswith.
_COST_TABLE: dict[str, tuple[float, float]] = {
    # (prompt_per_1M, completion_per_1M)
    "openai/gpt-4o": (2.50, 10.00),
    "openai/gpt-4o-mini": (0.15, 0.60),
    "openai/gpt-4.1": (2.00, 8.00),
    "openai/gpt-4.1-mini": (0.40, 1.60),
    "openai/gpt-4.1-nano": (0.10, 0.40),
    "openai/gpt-5": (2.00, 8.00),
    "openai/gpt-5.4": (2.00, 8.00),
    "openai/o1": (15.00, 60.00),
    "openai/o1-mini": (1.10, 4.40),
    "openai/o3": (2.00, 8.00),
    "openai/o3-mini": (1.10, 4.40),
    "openai/o4-mini": (1.10, 4.40),
    "anthropic/claude-sonnet": (3.00, 15.00),
    "anthropic/claude-3.5-sonnet": (3.00, 15.00),
    "anthropic/claude-3-opus": (15.00, 75.00),
    "anthropic/claude-opus": (15.00, 75.00),
    "anthropic/claude-haiku": (0.25, 1.25),
    "google/gemini-2.5-pro": (1.25, 10.00),
    "google/gemini-2.5-flash": (0.15, 0.60),
    "google/gemini-2.0-flash": (0.10, 0.40),
    "deepseek/deepseek-chat": (0.14, 0.28),
    "deepseek/deepseek-reasoner": (0.55, 2.19),
}


def _lookup_cost(model: str) -> tuple[float, float]:
    """Return (prompt_cost_per_1M, completion_cost_per_1M) for the model."""
    model_lower = model.lower()
    # Exact match first
    if model_lower in _COST_TABLE:
        return _COST_TABLE[model_lower]
    # Prefix match (e.g. "openai/gpt-4o-2024-08-06" → "openai/gpt-4o")
    for prefix, costs in sorted(_COST_TABLE.items(), key=lambda x: -len(x[0])):
        if model_lower.startswith(prefix):
            return costs
    return (0.0, 0.0)  # Unknown model — track tokens but not cost


@dataclass(slots=True)
class TokenSnapshot:
    """Immutable snapshot of token usage at a point in time."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    request_count: int = 0
    model: str = ""
    timestamp: float = field(default_factory=time)


@dataclass(slots=True)
class TokenTracker:
    """Accumulates token usage and cost across all LLM calls in a run.

    Thread-safe via asyncio.Lock. Use ``record()`` after every LLM call.
    """

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    request_count: int = 0
    model: str = ""
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    async def record(self, usage: dict[str, Any], model: str = "") -> TokenSnapshot:
        """Record usage from a single LLM response and return a running snapshot."""
        prompt = int(usage.get("prompt_tokens", 0))
        completion = int(usage.get("completion_tokens", 0))

        prompt_cost_1m, completion_cost_1m = _lookup_cost(model or self.model)
        call_cost = (prompt / 1_000_000 * prompt_cost_1m) + (completion / 1_000_000 * completion_cost_1m)

        async with self._lock:
            self.prompt_tokens += prompt
            self.completion_tokens += completion
            self.total_tokens += prompt + completion
            self.estimated_cost_usd += call_cost
            self.request_count += 1
            if model:
                self.model = model
            return self.snapshot()

    def snapshot(self) -> TokenSnapshot:
        return TokenSnapshot(
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            total_tokens=self.total_tokens,
            estimated_cost_usd=self.estimated_cost_usd,
            request_count=self.request_count,
            model=self.model,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "request_count": self.request_count,
            "model": self.model,
        }


# ── Global singleton ────────────────────────────────────────────────
_global_tracker: TokenTracker | None = None


def get_token_tracker() -> TokenTracker:
    global _global_tracker  # noqa: PLW0603
    if _global_tracker is None:
        _global_tracker = TokenTracker()
    return _global_tracker


def reset_token_tracker() -> None:
    global _global_tracker  # noqa: PLW0603
    _global_tracker = None
