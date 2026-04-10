from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from time import time
from typing import Any


class EventType(str, Enum):
    # Agent lifecycle
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    AGENT_SPAWNED = "agent_spawned"

    # Iteration lifecycle
    ITERATION_START = "iteration_start"
    ITERATION_END = "iteration_end"

    # LLM
    LLM_REQUEST = "llm_request"
    LLM_RESPONSE = "llm_response"
    LLM_ERROR = "llm_error"

    # Tool execution
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_COMPLETE = "tool_call_complete"
    TOOL_CALL_ERROR = "tool_call_error"

    # Agent thinking / planning
    THINKING = "thinking"
    REFLECTION = "reflection"

    # Findings
    FINDING_ADDED = "finding_added"

    # User interaction
    USER_MESSAGE = "user_message"

    # Scan lifecycle
    SCAN_STARTED = "scan_started"
    SCAN_COMPLETED = "scan_completed"

    # Persistence
    CHECKPOINT_SAVED = "checkpoint_saved"


@dataclass(slots=True)
class Event:
    type: EventType
    agent_id: str
    agent_name: str
    timestamp: float = field(default_factory=time)
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "timestamp": self.timestamp,
            "data": self.data,
        }


Subscriber = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """Async pub/sub event bus for structured agent telemetry.

    Singleton — use ``EventBus.instance()`` everywhere.
    """

    _instance: EventBus | None = None

    def __init__(self) -> None:
        self._subscribers: list[Subscriber] = []
        self._log_path: Path | None = None
        self._log_file: Any = None
        self._lock = asyncio.Lock()

    @classmethod
    def instance(cls) -> EventBus:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for tests)."""
        if cls._instance is not None and cls._instance._log_file is not None:
            cls._instance._log_file.close()
        cls._instance = None

    def set_log_path(self, path: Path) -> None:
        """Set the JSONL output file for persistent event logging."""
        path.parent.mkdir(parents=True, exist_ok=True)
        self._log_path = path
        self._log_file = open(path, "a", encoding="utf-8")  # noqa: SIM115

    def subscribe(self, callback: Subscriber) -> None:
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Subscriber) -> None:
        self._subscribers = [s for s in self._subscribers if s is not callback]

    async def emit(self, event: Event) -> None:
        """Publish an event to all subscribers and persist to JSONL."""
        # Write to log file synchronously (fast, append-only)
        if self._log_file is not None:
            self._log_file.write(json.dumps(event.to_dict(), default=str) + "\n")
            self._log_file.flush()

        # Notify subscribers (fire-and-forget, don't block the agent loop)
        for subscriber in self._subscribers:
            try:  # noqa: SIM105
                await subscriber(event)
            except Exception:  # noqa: BLE001, S110
                pass  # UI errors must never crash the agent

    def emit_sync(self, event: Event) -> None:
        """Non-async emit for use in sync contexts. Writes to log only."""
        if self._log_file is not None:
            self._log_file.write(json.dumps(event.to_dict(), default=str) + "\n")
            self._log_file.flush()

    def close(self) -> None:
        if self._log_file is not None:
            self._log_file.close()
            self._log_file = None
