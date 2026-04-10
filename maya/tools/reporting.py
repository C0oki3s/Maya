from __future__ import annotations

import hashlib
from time import time

from maya.agents.state import AgentState

from .registry import register_tool

_reported_hashes: set[str] = set()


def _finding_hash(title: str, category: str) -> str:
    raw = f"{title.lower().strip()}|{category.lower().strip()}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


@register_tool(sandbox_execution=False)
def report_vulnerability(
    title: str,
    severity: str,
    category: str,
    description: str,
    poc: str,
    impact: str,
    remediation: str,
    evidence: str = "",
    agent_state: AgentState | None = None,
) -> dict:
    """Record a vulnerability finding with deduplication."""
    finding_id = _finding_hash(title, category)
    if finding_id in _reported_hashes:
        return {"status": "duplicate", "id": finding_id}

    _reported_hashes.add(finding_id)
    finding = {
        "id": finding_id,
        "title": title,
        "severity": severity,
        "category": category,
        "description": description,
        "poc": poc,
        "impact": impact,
        "remediation": remediation,
        "evidence": evidence[:2000],
        "timestamp": time(),
    }
    if agent_state is not None:
        agent_state.add_finding(finding)
    return {"status": "ok", "finding": finding}


@register_tool(sandbox_execution=False)
def add_note(note: str, agent_state: AgentState | None = None) -> dict:
    """Store a note in the current agent context."""
    if agent_state is not None:
        agent_state.notes.append(note)
    return {"status": "ok", "note": note}


@register_tool(sandbox_execution=False)
def report_api_endpoint(
    url: str,
    method: str,
    auth_type: str,
    parameters: str = "{}",
    response_type: str = "application/json",
    notes: str = "",
    agent_state: AgentState | None = None,
) -> dict:
    """Record discovered API endpoint metadata."""
    endpoint = {
        "url": url,
        "method": method.upper(),
        "auth_type": auth_type,
        "parameters": parameters,
        "response_type": response_type,
        "notes": notes,
    }
    if agent_state is not None:
        agent_state.add_api_endpoint(endpoint)
    return {"status": "ok", "endpoint": endpoint}


@register_tool(sandbox_execution=False)
def update_todo(action: str, item: str = "", item_id: str = "", agent_state: AgentState | None = None) -> dict:
    """Manage agent todo list: add, complete, remove, list."""
    if agent_state is None:
        return {"status": "error", "message": "agent_state is required"}

    if action == "add":
        new_id = item_id or str(len(agent_state.todo_items) + 1)
        agent_state.todo_items.append({"id": new_id, "item": item, "done": False})
        return {"status": "ok", "todo": agent_state.todo_items[-1]}

    if action == "complete":
        for todo in agent_state.todo_items:
            if todo["id"] == item_id:
                todo["done"] = True
                return {"status": "ok", "todo": todo}
        return {"status": "error", "message": f"todo not found: {item_id}"}

    if action == "remove":
        before = len(agent_state.todo_items)
        agent_state.todo_items = [t for t in agent_state.todo_items if t["id"] != item_id]
        return {"status": "ok", "removed": before - len(agent_state.todo_items)}

    if action == "list":
        return {"status": "ok", "todos": agent_state.todo_items}

    return {"status": "error", "message": "unknown action"}


@register_tool(sandbox_execution=False)
def thinking(thought: str, agent_state: AgentState | None = None) -> dict:
    """Record the current reasoning step without side effects."""
    if agent_state is not None:
        agent_state.notes.append(f"thinking: {thought}")
    return {"status": "ok", "thought": thought}


@register_tool(sandbox_execution=False)
def agent_finish(report: str, agent_state: AgentState | None = None) -> dict:
    """Signal the current agent to complete."""
    if agent_state is not None:
        agent_state.add_note(f"agent_finish: {report}")
    return {"agent_completed": True, "report": report}


@register_tool(sandbox_execution=False)
def finish_scan(summary: str, agent_state: AgentState | None = None) -> dict:
    """Signal root scan completion."""
    if agent_state is not None:
        agent_state.add_note(f"finish_scan: {summary}")
    return {"scan_completed": True, "summary": summary}
