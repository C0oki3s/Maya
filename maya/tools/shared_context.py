from __future__ import annotations

import json
from time import time

from maya.agents.state import AgentState

from .registry import register_tool

_SHARED_CONTEXT: dict[str, object] = {
    "discovered_urls": [],
    "discovered_endpoints": [],
    "interesting_classes": [],
    "extracted_secrets": [],
    "bypasses_active": {},
    "decompiled_paths": {},
    "app_metadata": {},
    "notes": [],
}


def get_shared_context_snapshot() -> dict[str, object]:
    return dict(_SHARED_CONTEXT)


@register_tool(sandbox_execution=False)
def shared_context_write(key: str, value: str, agent_state: AgentState | None = None) -> dict:
    """Write key/value data into shared scan context."""
    parsed = value
    try:
        parsed = json.loads(value)
    except Exception:
        parsed = value

    _SHARED_CONTEXT[key] = parsed
    _SHARED_CONTEXT.setdefault("notes", [])
    if isinstance(_SHARED_CONTEXT["notes"], list):
        _SHARED_CONTEXT["notes"].append(
            {
                "ts": time(),
                "agent_id": agent_state.agent_id if agent_state else "unknown",
                "key": key,
            }
        )
    return {"status": "ok", "key": key}


@register_tool(sandbox_execution=False)
def shared_context_read(key: str = "", agent_state: AgentState | None = None) -> dict:
    """Read from shared scan context by key or return full context."""
    del agent_state
    if key:
        return {"status": "ok", "key": key, "value": _SHARED_CONTEXT.get(key)}
    return {"status": "ok", "context": _SHARED_CONTEXT}
