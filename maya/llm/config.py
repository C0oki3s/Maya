from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class LLMConfig:
    model: str = "mock/local"
    api_key: str | None = None
    api_base: str | None = None
    temperature: float = 0.1
    max_tokens: int = 8192
    max_retries: int = 3
    verbose: bool = False
    reasoning_effort: str = "high"

    def apply_overrides(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        api_base: str | None = None,
    ) -> LLMConfig:
        if model:
            self.model = model
        if api_key:
            self.api_key = api_key
        if api_base:
            self.api_base = api_base
        return self

    @classmethod
    def load(cls, config_path: Path | None = None) -> LLMConfig:
        cfg = cls()
        path = config_path or (Path.home() / ".maya" / "config.json")
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                cfg = cls(**{**asdict(cfg), **data})
            except Exception:  # noqa: S110
                pass  # invalid config file is non-fatal

        env_model = os.environ.get("MAYA_LLM")
        env_api_key = os.environ.get("LLM_API_KEY")
        env_api_base = os.environ.get("LLM_API_BASE")
        env_reasoning = os.environ.get("MAYA_REASONING_EFFORT")

        if env_model:
            cfg.model = env_model
        if env_api_key:
            cfg.api_key = env_api_key
        if env_api_base:
            cfg.api_base = env_api_base
        if env_reasoning:
            cfg.reasoning_effort = env_reasoning

        return cfg

    def persist(self, config_path: Path | None = None) -> None:
        path = config_path or (Path.home() / ".maya" / "config.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
