from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from maya.telemetry.event_bus import Event, EventBus, EventType

from .state import AgentState, AgentStatus


@dataclass(slots=True)
class AgentNode:
    agent_id: str
    name: str
    task: str
    status: AgentStatus
    parent_id: str | None
    children: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)


class AgentGraph:
    _instance: AgentGraph | None = None

    def __init__(self) -> None:
        self.nodes: dict[str, AgentNode] = {}
        self.edges: list[dict[str, str]] = []
        self._agent_messages: dict[str, list[dict[str, str]]] = {}
        self._agent_states: dict[str, AgentState] = {}
        self._agent_tasks: dict[str, asyncio.Task[Any]] = {}
        self._lock = asyncio.Lock()

    @classmethod
    def instance(cls) -> AgentGraph:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def register_agent(self, state: AgentState) -> None:
        async with self._lock:
            self._agent_states[state.agent_id] = state
            self.nodes[state.agent_id] = AgentNode(
                agent_id=state.agent_id,
                name=state.agent_name,
                task=state.task,
                status=state.status,
                parent_id=state.parent_id,
                skills=list(state.skills),
            )
            self._agent_messages.setdefault(state.agent_id, [])

            if state.parent_id and state.parent_id in self.nodes:
                self.nodes[state.parent_id].children.append(state.agent_id)
                self.edges.append(
                    {
                        "from": state.parent_id,
                        "to": state.agent_id,
                        "type": "delegation",
                    }
                )

    async def update_status(self, agent_id: str, status: AgentStatus) -> None:
        async with self._lock:
            if agent_id in self.nodes:
                self.nodes[agent_id].status = status

    async def view(self) -> dict[str, Any]:
        async with self._lock:
            return {
                "total_agents": len(self.nodes),
                "active_agents": sum(1 for n in self.nodes.values() if n.status == AgentStatus.RUNNING),
                "nodes": [
                    {
                        "agent_id": n.agent_id,
                        "name": n.name,
                        "task": n.task,
                        "status": n.status.value,
                        "parent_id": n.parent_id,
                        "children": list(n.children),
                    }
                    for n in self.nodes.values()
                ],
                "edges": list(self.edges),
            }

    async def send_message(self, target_agent_id: str, from_agent_id: str, message: str) -> dict[str, Any]:
        async with self._lock:
            if target_agent_id not in self.nodes:
                return {"status": "error", "message": f"unknown target agent: {target_agent_id}"}

            self._agent_messages.setdefault(target_agent_id, []).append({"from": from_agent_id, "content": message})

            target_state = self._agent_states.get(target_agent_id)
            if target_state is not None:
                target_state.add_message(
                    "user",
                    f"<message from='{from_agent_id}'>{message}</message>",
                )

            return {"status": "ok"}

    async def create_agent(
        self,
        parent_state: AgentState,
        task: str,
        name: str,
        skills: list[str],
        agent_class_name: str = "MayaAgent",
    ) -> dict[str, Any]:
        from .base_agent import get_registered_agent_class

        cls = get_registered_agent_class(agent_class_name)
        if cls is None:
            return {"status": "error", "message": f"unknown agent class: {agent_class_name}"}

        child_agent = cls(
            task=task,
            name=name,
            skills=skills,
            parent_id=parent_state.agent_id,
            max_iterations=parent_state.max_iterations,
            target_app=parent_state.target_app,
            device_id=parent_state.connected_device,
            platform=parent_state.device_platform,
        )

        await child_agent.initialize()
        task_obj = asyncio.create_task(child_agent.agent_loop())

        async with self._lock:
            self._agent_tasks[child_agent.state.agent_id] = task_obj

        await EventBus.instance().emit(
            Event(
                type=EventType.AGENT_SPAWNED,
                agent_id=child_agent.state.agent_id,
                agent_name=child_agent.state.agent_name,
                data={"parent_id": parent_state.agent_id, "task": task, "skills": skills},
            )
        )

        return {
            "status": "ok",
            "agent_id": child_agent.state.agent_id,
            "name": child_agent.state.agent_name,
            "task": child_agent.state.task,
        }
