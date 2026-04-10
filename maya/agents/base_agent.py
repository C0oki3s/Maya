from __future__ import annotations

import asyncio
import secrets
from abc import ABC, abstractmethod
from collections import Counter
from pathlib import Path
from time import time
from typing import Any

from maya.agents.checkpointing import save_checkpoint
from maya.llm.llm import LLMClient, LLMProtocol
from maya.llm.memory_compressor import MemoryCompressor
from maya.llm.token_tracker import get_token_tracker
from maya.llm.utils import normalize_tool_format, parse_tool_invocations
from maya.runtime.docker_runtime import DockerRuntime
from maya.telemetry.event_bus import Event, EventBus, EventType
from maya.tools.executor import _normalize_tool_result, process_tool_invocations

from .graph import AgentGraph
from .state import AgentState, AgentStatus

_agent_registry: dict[str, type[BaseAgent]] = {}


def get_registered_agent_class(name: str) -> type[BaseAgent] | None:
    return _agent_registry.get(name)


class AgentMeta(type(ABC)):
    def __init__(cls, name: str, bases: tuple[type, ...], namespace: dict[str, Any]) -> None:
        super().__init__(name, bases, namespace)
        if name != "BaseAgent":
            _agent_registry[name] = cls


class BaseAgent(ABC, metaclass=AgentMeta):
    def __init__(
        self,
        task: str,
        name: str,
        llm: LLMProtocol | None = None,
        skills: list[str] | None = None,
        parent_id: str | None = None,
        max_iterations: int = 50,
        target_app: str | None = None,
        device_id: str | None = None,
        platform: str | None = None,
        run_name: str = "default",
    ) -> None:
        self.state = AgentState(
            agent_name=name,
            task=task,
            parent_id=parent_id,
            skills=skills or [],
            max_iterations=max_iterations,
            target_app=target_app,
            connected_device=device_id,
            device_platform=platform,
        )
        self.llm = llm or LLMClient()
        self._stop_event = asyncio.Event()
        self.run_name = run_name
        self._compressor = MemoryCompressor()
        self._runtime = DockerRuntime()

    @abstractmethod
    def build_system_prompt(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def on_scan_complete(self, findings: list[dict[str, Any]]) -> None:
        raise NotImplementedError

    def _emit(self, event_type: EventType, data: dict[str, Any] | None = None) -> None:
        """Fire-and-forget event emission."""
        event = Event(
            type=event_type,
            agent_id=self.state.agent_id,
            agent_name=self.state.agent_name,
            data=data or {},
        )
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(EventBus.instance().emit(event))
        except RuntimeError:
            EventBus.instance().emit_sync(event)

    async def initialize(self) -> None:
        self.state.status = AgentStatus.RUNNING
        self.state.started_at = time()

        token = secrets.token_hex(16)
        sandbox = self._runtime.create_sandbox(
            agent_id=self.state.agent_id,
            auth_token=token,
            local_sources=[str(Path.cwd())],
        )
        self.state.sandbox_info = {
            "workspace_id": sandbox.workspace_id,
            "server_url": sandbox.server_url,
            "auth_token": sandbox.auth_token,
            "agent_id": sandbox.agent_id,
        }

        self.state.add_message("system", self.build_system_prompt())
        self.state.add_message("user", self.state.task)
        await AgentGraph.instance().register_agent(self.state)
        self._emit(EventType.AGENT_STARTED, {"task": self.state.task, "role": getattr(self, "role", "root")})

    def _check_progress(self) -> str | None:
        """Detect looping or stalling and return a reflection prompt if needed."""
        # Early scan phases should establish target and attack surface quickly.
        if self.state.iteration_count >= 5 and not self.state.decompiled_paths and not self.state.findings:
            return (
                "<reflection>Flow nudge: You have not established static artifacts yet. "
                "Run an enumeration-first sequence now: identify target binary/source, "
                "decompile/analyze manifest, enumerate exported components/deep links/API hosts, "
                "write results to shared context, then branch into focused dynamic and API testing. "
                "Avoid generic retries and prioritize concrete attack-surface mapping.</reflection>"
            )

        recent_tool_calls: list[str] = []
        for msg in reversed(self.state.messages):
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                # Extract tool names from assistant messages that contain tool calls
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("<tool_call>") or "<toolName>" in stripped:
                        recent_tool_calls.append(stripped)
            if len(recent_tool_calls) >= 5:
                break

        if len(recent_tool_calls) >= 5:
            counts = Counter(recent_tool_calls)
            most_common_count = counts.most_common(1)[0][1] if counts else 0
            if most_common_count >= 3:
                return (
                    "<reflection>You appear to be repeating similar tool calls. "
                    "Switch to the next flow stage: (1) enumerate unresolved attack surface, "
                    "(2) validate one concrete lead end-to-end, (3) record evidence and move to the next lead. "
                    "Do not repeat the same tool pattern without new evidence.</reflection>"
                )

        # Approaching iteration limit with no findings
        progress_ratio = self.state.iteration_count / max(self.state.max_iterations, 1)
        if progress_ratio >= 0.8 and not self.state.findings:
            return (
                "<reflection>You have used 80% of your iteration budget with no "
                "findings recorded yet. Prioritize your remaining iterations â€” "
                "focus on the most likely vulnerabilities or escalate.</reflection>"
            )

        return None

    async def _process_iteration(self) -> bool:
        self._emit(EventType.ITERATION_START, {"iteration": self.state.iteration_count})

        history = self._compressor.maybe_compress(self.state.get_conversation_history())
        self._emit(EventType.LLM_REQUEST, {"message_count": len(history)})
        response = await self.llm.generate(history)
        content = response.content or ""
        self.state.add_message("assistant", content)

        tracker = get_token_tracker()
        snap = tracker.snapshot()
        self._emit(
            EventType.LLM_RESPONSE,
            {
                "content_length": len(content),
                "model": response.model or "",
                "usage": response.usage or {},
                "finish_reason": response.finish_reason or "",
                "total_tokens": snap.total_tokens,
                "total_prompt_tokens": snap.prompt_tokens,
                "total_completion_tokens": snap.completion_tokens,
                "total_cost_usd": snap.estimated_cost_usd,
                "total_requests": snap.request_count,
            },
        )

        normalized = normalize_tool_format(content)
        tool_calls = parse_tool_invocations(normalized)

        if not tool_calls:
            # LLM returned text with no tool calls â€” this is "thinking"
            self._emit(EventType.THINKING, {"content": content[:2000]})
            self._emit(EventType.ITERATION_END, {"iteration": self.state.iteration_count, "tool_calls": 0})
            return False

        results = await process_tool_invocations(tool_calls, self.state)
        for i, result in enumerate(results):
            if isinstance(result, dict) and (result.get("scan_completed") or result.get("agent_completed")):
                self._emit(
                    EventType.ITERATION_END,
                    {"iteration": self.state.iteration_count, "tool_calls": len(tool_calls), "completed": True},
                )
                return True
            tool_name = str(tool_calls[i].get("toolName", "unknown"))
            formatted = _normalize_tool_result(tool_name, result, 0.0)
            self.state.add_message("user", formatted)
        self._emit(EventType.ITERATION_END, {"iteration": self.state.iteration_count, "tool_calls": len(tool_calls)})
        return False

    async def agent_loop(self) -> dict[str, Any]:
        while not self.state.should_terminate() and not self._stop_event.is_set():
            self.state.iteration_count += 1

            # Reflection checkpoint every 5 iterations
            if self.state.iteration_count % 5 == 0:
                reflection = self._check_progress()
                if reflection:
                    self.state.add_message("user", reflection)

            try:
                should_stop = await self._process_iteration()
                checkpoint_path = save_checkpoint(self.state, run_name=self.run_name, interval=5)
                if checkpoint_path is not None:
                    self._emit(
                        EventType.CHECKPOINT_SAVED,
                        {
                            "path": str(checkpoint_path),
                            "iteration": self.state.iteration_count,
                            "tool_calls": self.state.tool_call_count,
                            "findings": len(self.state.findings),
                        },
                    )
                if should_stop:
                    break
            except Exception as exc:  # noqa: BLE001
                self.state.record_tool_call(False)
                self.state.add_message("user", f"<e>Error: {exc}</e>")
                self._emit(EventType.AGENT_FAILED, {"error": str(exc), "iteration": self.state.iteration_count})
                if self.state.tool_errors > 10:
                    self.state.status = AgentStatus.FAILED
                    break

        final_status = AgentStatus.COMPLETED if self.state.status == AgentStatus.RUNNING else self.state.status
        self.state.status = final_status
        self.state.finished_at = time()
        self._runtime.destroy_sandbox(self.state.agent_id)
        await AgentGraph.instance().update_status(self.state.agent_id, self.state.status)
        await self.on_scan_complete(self.state.findings)
        self._emit(
            EventType.AGENT_COMPLETED if final_status == AgentStatus.COMPLETED else EventType.AGENT_FAILED,
            {
                "status": final_status.value,
                "iterations": self.state.iteration_count,
                "tool_calls": self.state.tool_call_count,
                "findings": len(self.state.findings),
            },
        )
        return {
            "findings": self.state.findings,
            "api_endpoints": self.state.api_endpoints,
            "intercepted_traffic": self.state.intercepted_traffic,
            "iterations": self.state.iteration_count,
            "tool_calls": self.state.tool_call_count,
            "status": self.state.status.value,
        }
