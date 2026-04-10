from __future__ import annotations

import asyncio
import os
from time import monotonic
from typing import Any

import httpx

from maya.agents.state import AgentState
from maya.llm.request_queue import request_queue
from maya.telemetry.event_bus import Event, EventBus, EventType

from .registry import get_tool, get_tool_schema, needs_agent_state, should_execute_in_sandbox


def _normalize_tool_result(tool_name: str, raw: Any, duration: float) -> str:
    """Wrap raw tool output in a consistent XML structure for the LLM."""
    if isinstance(raw, dict):
        status = "error" if raw.get("error") else "success"
        if status == "error":
            summary = raw.get("error", "unknown error")
            details = ""
        else:
            summary = raw.get("summary", raw.get("status", "completed"))
            details_parts = [f"{k}: {v}" for k, v in raw.items() if k not in ("summary", "status", "error")]
            details = "\n  ".join(details_parts)
    else:
        status = "success"
        summary = str(raw)[:200] if raw else "done"
        details = str(raw) if raw else ""

    parts = [f'<tool_result tool="{tool_name}" status="{status}" duration="{duration:.1f}s">']
    parts.append(f"<summary>{summary}</summary>")
    if details:
        parts.append(f"<details>\n  {details}\n</details>")
    parts.append("</tool_result>")
    return "\n".join(parts)


def validate_tool_availability(tool_name: str) -> tuple[bool, str]:
    if get_tool(tool_name) is None:
        return False, f"Unknown tool: {tool_name}"
    return True, ""


def _validate_tool_arguments(tool_name: str, args: dict[str, Any]) -> tuple[bool, str]:
    schema = get_tool_schema(tool_name)
    if schema is None:
        return False, f"Tool schema not found for {tool_name}"

    required = schema["required"]
    allowed = schema["params"]

    missing = [p for p in sorted(required) if not str(args.get(p, "")).strip()]
    unknown = [p for p in sorted(args.keys()) if p not in allowed]

    if missing:
        return False, f"Missing required params for {tool_name}: {', '.join(missing)}"
    if unknown:
        return False, f"Unknown params for {tool_name}: {', '.join(unknown)}"
    return True, ""


async def _execute_tool_locally(tool_name: str, args: dict[str, Any], agent_state: AgentState) -> Any:
    func = get_tool(tool_name)
    if func is None:
        return {"error": f"Unknown tool: {tool_name}"}

    kwargs = dict(args)
    if needs_agent_state(func):
        kwargs["agent_state"] = agent_state

    try:
        result = func(**kwargs)
        if asyncio.iscoroutine(result):
            result = await result
        agent_state.record_tool_call(True)
        return result
    except Exception as exc:  # noqa: BLE001
        agent_state.record_tool_call(False)
        return {"error": str(exc), "tool": tool_name}


async def _execute_tool_in_sandbox(tool_name: str, args: dict[str, Any], agent_state: AgentState) -> Any:
    sandbox = agent_state.sandbox_info or {}
    server_url = sandbox.get("server_url")
    auth_token = sandbox.get("auth_token")

    if not server_url or not auth_token:
        return await _execute_tool_locally(tool_name, args, agent_state)

    timeout_s = int(os.environ.get("MAYA_SANDBOX_TIMEOUT", "120")) + 30
    payload = {
        "agent_id": agent_state.agent_id,
        "tool_name": tool_name,
        "kwargs": args,
    }
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            response = await client.post(f"{server_url}/execute", json=payload, headers=headers)
            response.raise_for_status()
            body = response.json()
    except Exception as exc:  # noqa: BLE001
        agent_state.record_tool_call(False)
        return {
            "error": f"sandbox execution failed: {exc}",
            "tool": tool_name,
        }

    if body.get("error"):
        agent_state.record_tool_call(False)
        return {"error": body["error"], "tool": tool_name}

    agent_state.record_tool_call(True)
    return body.get("result")


async def execute_tool(tool_name: str, args: dict[str, Any], agent_state: AgentState) -> Any:
    ok, err = validate_tool_availability(tool_name)
    if not ok:
        agent_state.record_tool_call(False)
        return {"error": err}

    ok, err = _validate_tool_arguments(tool_name, args)
    if not ok:
        agent_state.record_tool_call(False)
        return {"error": err}

    bus = EventBus.instance()
    await bus.emit(
        Event(
            type=EventType.TOOL_CALL_START,
            agent_id=agent_state.agent_id,
            agent_name=agent_state.agent_name,
            data={
                "tool": tool_name,
                "args": {k: str(v)[:200] for k, v in args.items()},
                "sandbox": should_execute_in_sandbox(tool_name),
            },
        )
    )

    await request_queue.throttle(tool_name)

    t0 = monotonic()
    if should_execute_in_sandbox(tool_name):
        raw = await _execute_tool_in_sandbox(tool_name, args, agent_state)
    else:
        raw = await _execute_tool_locally(tool_name, args, agent_state)
    duration = monotonic() - t0

    is_error = isinstance(raw, dict) and raw.get("error")
    await bus.emit(
        Event(
            type=EventType.TOOL_CALL_ERROR if is_error else EventType.TOOL_CALL_COMPLETE,
            agent_id=agent_state.agent_id,
            agent_name=agent_state.agent_name,
            data={"tool": tool_name, "duration": round(duration, 2), "error": raw.get("error") if is_error else None},
        )
    )

    return raw


async def process_tool_invocations(
    tool_calls: list[dict[str, Any]],
    agent_state: AgentState,
) -> list[Any]:
    results: list[Any] = []
    for call in tool_calls:
        tool_name = str(call.get("toolName", ""))
        args = call.get("args", {}) or {}
        results.append(await execute_tool(tool_name, args, agent_state))
    return results
