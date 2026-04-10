from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .state import AgentState, AgentStatus


def save_checkpoint(state: AgentState, run_name: str, interval: int = 5) -> Path | None:
    if state.iteration_count % interval != 0:
        return None

    base = Path("maya_runs") / run_name / "checkpoints"
    base.mkdir(parents=True, exist_ok=True)
    target = base / f"{state.agent_id}_iter_{state.iteration_count}.json"
    target.write_text(json.dumps(asdict(state), indent=2, default=str), encoding="utf-8")
    return target


def load_latest_checkpoint(run_name: str, agent_id: str | None = None) -> dict[str, Any] | None:
    base = Path("maya_runs") / run_name / "checkpoints"
    if not base.exists():
        return None

    candidates = sorted(base.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for c in candidates:
        if agent_id and not c.name.startswith(agent_id):
            continue
        return json.loads(c.read_text(encoding="utf-8"))
    return None


def apply_checkpoint(state: AgentState, payload: dict[str, Any]) -> AgentState:
    state.messages = payload.get("messages", state.messages)
    state.findings = payload.get("findings", state.findings)
    state.api_endpoints = payload.get("api_endpoints", state.api_endpoints)
    state.todo_items = payload.get("todo_items", state.todo_items)
    state.notes = payload.get("notes", state.notes)
    state.tool_call_count = int(payload.get("tool_call_count", state.tool_call_count))
    state.iteration_count = int(payload.get("iteration_count", state.iteration_count))
    state.status = AgentStatus(payload.get("status", state.status.value))
    return state
