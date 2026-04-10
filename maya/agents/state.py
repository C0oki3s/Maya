from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import time
from typing import Any
from uuid import uuid4


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


@dataclass(slots=True)
class AgentState:
    agent_name: str
    task: str
    parent_id: str | None = None
    skills: list[str] = field(default_factory=list)
    max_iterations: int = 50
    agent_id: str = field(default_factory=lambda: str(uuid4())[:8])
    status: AgentStatus = AgentStatus.IDLE
    messages: list[dict[str, Any]] = field(default_factory=list)
    tool_call_count: int = 0
    tool_errors: int = 0
    iteration_count: int = 0
    sandbox_id: str | None = None
    sandbox_token: str | None = None
    sandbox_info: dict[str, Any] = field(default_factory=dict)
    connected_device: str | None = None
    device_platform: str | None = None
    target_app: str | None = None
    findings: list[dict[str, Any]] = field(default_factory=list)
    api_endpoints: list[dict[str, Any]] = field(default_factory=list)
    decompiled_paths: dict[str, str] = field(default_factory=dict)
    intercepted_traffic: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    todo_items: list[dict[str, Any]] = field(default_factory=list)
    started_at: float | None = None
    finished_at: float | None = None

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        msg: dict[str, Any] = {
            "role": role,
            "content": content,
            "timestamp": time(),
        }
        msg.update(kwargs)
        self.messages.append(msg)

    def get_conversation_history(self) -> list[dict[str, str]]:
        allowed = {"system", "user", "assistant", "tool"}
        history: list[dict[str, str]] = []
        for msg in self.messages:
            if msg.get("role") in allowed:
                history.append({"role": msg["role"], "content": str(msg.get("content", ""))})
        return history

    def add_finding(self, finding: dict[str, Any]) -> None:
        enriched = dict(finding)
        enriched.setdefault("agent_id", self.agent_id)
        enriched.setdefault("agent_name", self.agent_name)
        enriched.setdefault("timestamp", time())
        self.findings.append(enriched)

    def add_api_endpoint(self, endpoint: dict[str, Any]) -> None:
        enriched = dict(endpoint)
        enriched.setdefault("discovered_by", self.agent_id)
        enriched.setdefault("timestamp", time())
        self.api_endpoints.append(enriched)

    def add_note(self, note: str) -> None:
        self.notes.append(note)

    def record_tool_call(self, success: bool) -> None:
        self.tool_call_count += 1
        if not success:
            self.tool_errors += 1

    def should_terminate(self) -> bool:
        if self.iteration_count >= self.max_iterations:
            return True
        return self.status in {
            AgentStatus.COMPLETED,
            AgentStatus.FAILED,
            AgentStatus.TERMINATED,
        }

    def to_summary(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self.status.value,
            "iteration_count": self.iteration_count,
            "tool_calls": self.tool_call_count,
            "tool_errors": self.tool_errors,
            "findings": len(self.findings),
        }
