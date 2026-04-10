from __future__ import annotations

import asyncio
import fnmatch
from collections import deque
from time import time


class RequestQueue:
    def __init__(self) -> None:
        self._history: dict[str, deque[float]] = {}
        self._limits = {
            "frida_*": {"max_per_minute": 30, "cooldown_seconds": 2.0},
            "caido_*": {"max_per_minute": 60, "cooldown_seconds": 0.5},
            "api_fuzz_*": {"max_per_minute": 10, "cooldown_seconds": 5.0},
            "llm_call": {"max_per_minute": 20, "cooldown_seconds": 3.0},
        }

    def _match_rule(self, name: str) -> tuple[str, dict] | None:
        for pattern, rule in self._limits.items():
            if fnmatch.fnmatch(name, pattern):
                return pattern, rule
        return None

    async def throttle(self, name: str) -> None:
        match = self._match_rule(name)
        if match is None:
            return

        pattern, rule = match
        now = time()
        q = self._history.setdefault(pattern, deque())
        while q and now - q[0] > 60:
            q.popleft()

        max_per_minute = int(rule["max_per_minute"])
        cooldown = float(rule["cooldown_seconds"])

        if len(q) >= max_per_minute:
            wait_for = 60 - (now - q[0])
            if wait_for > 0:
                await asyncio.sleep(wait_for)

        await asyncio.sleep(cooldown)
        q.append(time())


request_queue = RequestQueue()
