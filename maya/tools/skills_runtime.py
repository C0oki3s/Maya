from __future__ import annotations

from pathlib import Path

from maya.agents.state import AgentState
from maya.skills import (
    get_available_skills,
    list_available_skills_with_sources,
    load_skills,
)

from .registry import register_tool


def _vulndb_paths() -> list[Path]:
    home = Path.home() / ".maya" / "vulndb"
    return [home]


@register_tool(sandbox_execution=False)
def reload_skills(agent_state: AgentState | None = None) -> dict:
    """Reload available skills from configured search paths."""
    del agent_state
    return {"status": "ok", "skills": get_available_skills()}


@register_tool(sandbox_execution=False)
def list_available_skills(agent_state: AgentState | None = None) -> dict:
    """List loaded skills with source paths."""
    del agent_state
    return {"status": "ok", "skills": list_available_skills_with_sources()}


@register_tool(sandbox_execution=False)
def inject_skill(skill_name: str, agent_state: AgentState | None = None) -> dict:
    """Inject skill content into running agent conversation as dynamic skill."""
    loaded = load_skills([skill_name])
    content = loaded.get(skill_name)
    if content is None:
        return {"status": "error", "message": f"skill not found: {skill_name}"}

    if agent_state is not None:
        agent_state.add_message("user", f"<dynamic_skill name='{skill_name}'>{content}</dynamic_skill>")

    return {"status": "ok", "skill": skill_name}


@register_tool(sandbox_execution=False)
def search_skills(keyword: str, agent_state: AgentState | None = None) -> dict:
    """Search loaded skills for a keyword match."""
    del agent_state
    all_skills = load_skills([s["skill"] for s in list_available_skills_with_sources()])
    hits = []
    needle = keyword.lower().strip()
    for name, content in all_skills.items():
        if needle in content.lower():
            hits.append(name)
    return {"status": "ok", "keyword": keyword, "matches": sorted(set(hits))}


@register_tool(sandbox_execution=False)
def lookup_vulnerability_knowledge(query: str, agent_state: AgentState | None = None) -> dict:
    """Lookup vulnerability knowledge files from ~/.maya/vulndb by keyword."""
    del agent_state
    needle = query.lower().strip()
    matches: list[dict[str, str]] = []

    for root in _vulndb_paths():
        if not root.exists():
            continue
        for md in root.rglob("*.md"):
            content = md.read_text(encoding="utf-8")
            if needle in md.name.lower() or needle in content.lower():
                matches.append({"path": str(md), "content": content[:4000]})

    return {"status": "ok", "query": query, "results": matches}
