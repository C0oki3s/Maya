from __future__ import annotations

import hashlib
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


class LoopStage(str, Enum):
    ENUMERATE = "enumerate"
    VALIDATE = "validate"
    EXPLOIT = "exploit"
    REPORT = "report"


class LeadState(str, Enum):
    NEW = "new"
    VALIDATED = "validated"
    EXPLOITED = "exploited"
    REPORTED = "reported"
    DISCARDED = "discarded"


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
    loop_stage: str = LoopStage.ENUMERATE.value
    leads: list[dict[str, Any]] = field(default_factory=list)
    decision_history: list[dict[str, Any]] = field(default_factory=list)
    sandbox_mode: str = "strict"
    decision_timeout_seconds: int = 30
    decision_mode: str = "human_or_auto"
    scan_time_budget_minutes: float = 60.0
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

    def add_lead(
        self,
        *,
        title: str,
        source: str,
        evidence: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        seed = f"{source.lower().strip()}|{title.lower().strip()}"
        lead_id = hashlib.sha256(seed.encode()).hexdigest()[:16]
        for lead in self.leads:
            if lead.get("id") == lead_id:
                return lead

        lead = {
            "id": lead_id,
            "title": title,
            "source": source,
            "evidence": evidence[:2000],
            "metadata": metadata or {},
            "state": LeadState.NEW.value,
            "attempts": 0,
            "created_at": time(),
            "updated_at": time(),
        }
        self.leads.append(lead)
        return lead

    def mark_first_lead(self, from_state: LeadState, to_state: LeadState) -> dict[str, Any] | None:
        for lead in self.leads:
            if lead.get("state") == from_state.value:
                lead["state"] = to_state.value
                lead["updated_at"] = time()
                if to_state == LeadState.EXPLOITED:
                    lead["attempts"] = int(lead.get("attempts", 0)) + 1
                return lead
        return None

    def set_loop_stage(self, stage: LoopStage) -> bool:
        if self.loop_stage == stage.value:
            return False
        self.loop_stage = stage.value
        return True

    def recompute_loop_stage(self) -> LoopStage:
        states = [lead.get("state") for lead in self.leads]
        if LeadState.EXPLOITED.value in states:
            return LoopStage.REPORT
        if LeadState.VALIDATED.value in states:
            return LoopStage.EXPLOIT
        if LeadState.NEW.value in states:
            return LoopStage.VALIDATE
        return LoopStage.ENUMERATE

    def add_decision(self, record: dict[str, Any]) -> None:
        self.decision_history.append(record)

    def budget_exhausted(self) -> bool:
        if self.started_at is None:
            return False
        return (time() - self.started_at) >= self.scan_time_budget_minutes * 60

    def should_terminate(self) -> bool:
        if self.iteration_count >= self.max_iterations:
            return True
        if self.budget_exhausted():
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
            "loop_stage": self.loop_stage,
            "leads": len(self.leads),
        }
