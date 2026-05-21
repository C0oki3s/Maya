from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from time import time
from typing import Any

from maya.agents.state import AgentState
from maya.telemetry.event_bus import Event, EventBus, EventType
from maya.tools.shared_context import append_decision_record


@dataclass(slots=True)
class DecisionRequest:
    prompt: str
    options: list[str]
    safe_default: str
    timeout_seconds: int = 30
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DecisionResponse:
    selected_option: str
    note: str = ""
    source: str = "auto"


DecisionHandler = Callable[[DecisionRequest], Awaitable[DecisionResponse]]


class DecisionBroker:
    def __init__(self) -> None:
        self.decision_mode = "human_or_auto"
        self.timeout_seconds = 30
        self._ui_handler: DecisionHandler | None = None

    def configure(self, *, decision_mode: str, timeout_seconds: int) -> None:
        self.decision_mode = decision_mode
        self.timeout_seconds = max(1, int(timeout_seconds))

    def set_ui_handler(self, handler: DecisionHandler | None) -> None:
        self._ui_handler = handler

    async def request(self, req: DecisionRequest, agent_state: AgentState) -> DecisionResponse:
        timeout_seconds = max(1, int(req.timeout_seconds or self.timeout_seconds))
        await EventBus.instance().emit(
            Event(
                type=EventType.DECISION_REQUESTED,
                agent_id=agent_state.agent_id,
                agent_name=agent_state.agent_name,
                data={
                    "prompt": req.prompt[:300],
                    "options": req.options,
                    "safe_default": req.safe_default,
                    "timeout_seconds": timeout_seconds,
                    "context": {k: str(v)[:200] for k, v in req.context.items()},
                },
            )
        )

        if self._ui_handler is not None:
            try:
                response = await asyncio.wait_for(self._ui_handler(req), timeout=timeout_seconds)
            except TimeoutError:
                response = DecisionResponse(selected_option=req.safe_default, source="auto", note="ui timeout")
        elif self.decision_mode == "human_or_auto":
            response = await self._request_console(req, timeout_seconds)
        else:
            response = DecisionResponse(selected_option=req.safe_default, source="auto", note="auto mode")

        record = {
            "timestamp": time(),
            "agent_id": agent_state.agent_id,
            "agent_name": agent_state.agent_name,
            "prompt": req.prompt,
            "options": req.options,
            "selected_option": response.selected_option,
            "note": response.note,
            "source": response.source,
            "context": req.context,
        }
        append_decision_record(record)
        agent_state.add_decision(record)
        agent_state.add_message(
            "user",
            "<decision>"
            f"<prompt>{req.prompt}</prompt>"
            f"<selected>{response.selected_option}</selected>"
            f"<source>{response.source}</source>"
            f"<note>{response.note}</note>"
            f"<context>{json.dumps(req.context, default=str)[:1000]}</context>"
            "</decision>",
        )

        event_type = EventType.DECISION_AUTO_DEFAULTED if response.source == "auto" else EventType.DECISION_ANSWERED
        await EventBus.instance().emit(
            Event(
                type=event_type,
                agent_id=agent_state.agent_id,
                agent_name=agent_state.agent_name,
                data={
                    "selected_option": response.selected_option,
                    "note": response.note[:300],
                    "source": response.source,
                },
            )
        )
        return response

    async def _request_console(self, req: DecisionRequest, timeout_seconds: int) -> DecisionResponse:
        if not sys.stdin.isatty():
            return DecisionResponse(selected_option=req.safe_default, source="auto", note="non-interactive")

        options = req.options or [req.safe_default]
        lines = ["\n[decision gate] " + req.prompt]
        for i, opt in enumerate(options, start=1):
            lines.append(f"  {i}. {opt}")
        lines.append(f"  default (timeout {timeout_seconds}s): {req.safe_default}")
        sys.stderr.write("\n".join(lines) + "\n")
        sys.stderr.flush()

        loop = asyncio.get_running_loop()
        try:
            raw_choice = await asyncio.wait_for(
                loop.run_in_executor(None, input, "Choose option number: "),
                timeout=timeout_seconds,
            )
        except TimeoutError:
            return DecisionResponse(selected_option=req.safe_default, source="auto", note="timeout")

        selected = req.safe_default
        try:
            idx = int(raw_choice.strip()) - 1
            if 0 <= idx < len(options):
                selected = options[idx]
        except Exception:  # noqa: BLE001
            selected = req.safe_default

        try:
            note = await asyncio.wait_for(
                loop.run_in_executor(None, input, "Optional note (or Enter): "),
                timeout=max(5, timeout_seconds // 2),
            )
        except TimeoutError:
            note = ""

        return DecisionResponse(selected_option=selected, note=str(note).strip(), source="human")


_BROKER: DecisionBroker | None = None


def get_decision_broker() -> DecisionBroker:
    global _BROKER  # noqa: PLW0603
    if _BROKER is None:
        _BROKER = DecisionBroker()
    return _BROKER
