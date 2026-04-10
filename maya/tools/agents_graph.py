from __future__ import annotations

from maya.agents.graph import AgentGraph
from maya.agents.state import AgentState

from .registry import register_tool


def _parse_skills(skills: str) -> list[str]:
    return [s.strip() for s in skills.split(",") if s.strip()]


@register_tool(sandbox_execution=False)
async def create_agent(
    task: str,
    name: str,
    skills: str = "",
    agent_class: str = "MayaAgent",
    agent_state: AgentState | None = None,
) -> dict:
    """Spawn a child agent for a subtask."""
    if agent_state is None:
        return {"status": "error", "message": "agent_state is required"}

    return await AgentGraph.instance().create_agent(
        parent_state=agent_state,
        task=task,
        name=name,
        skills=_parse_skills(skills),
        agent_class_name=agent_class,
    )


@register_tool(sandbox_execution=False)
async def view_agent_graph(agent_state: AgentState | None = None) -> dict:
    """View full agent graph status and relationships."""
    del agent_state
    return await AgentGraph.instance().view()


@register_tool(sandbox_execution=False)
async def send_message_to_agent(
    target_agent_id: str,
    message: str,
    agent_state: AgentState | None = None,
) -> dict:
    """Send a message from the current agent to another agent."""
    if agent_state is None:
        return {"status": "error", "message": "agent_state is required"}

    return await AgentGraph.instance().send_message(
        target_agent_id=target_agent_id,
        from_agent_id=agent_state.agent_id,
        message=message,
    )
