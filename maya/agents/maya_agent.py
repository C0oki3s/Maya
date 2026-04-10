from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Template

import maya.tools  # noqa: F401
from maya.skills import collect_skill_warnings, load_skills, resolve_skill_dependencies, validate_skill_names
from maya.tools.registry import get_tools_prompt

from .base_agent import BaseAgent


class MayaAgent(BaseAgent):
    _template_path = Path(__file__).parent / "MayaAgent" / "system_prompt.jinja"

    def __init__(
        self,
        task: str,
        name: str = "maya_root",
        targets: list[dict[str, str]] | None = None,
        instruction: str = "",
        scan_mode: str = "quick",
        role: str = "root",
        run_name: str = "default",
        **kwargs: Any,
    ) -> None:
        super().__init__(task=task, name=name, run_name=run_name, **kwargs)
        self.targets = targets or []
        self.instruction = instruction
        self.scan_mode = scan_mode
        self.role = role

    def _role_modules(self) -> set[str]:
        base = {"reporting", "agents_graph", "skills_runtime", "shared_context"}
        role_map = {
            "root": base | {"terminal", "caido_tool", "device_bridge", "apk_tool", "frida_tool"},
            "static": base | {"apk_tool", "mobsf_tool", "terminal"},
            "dynamic": base | {"frida_tool", "device_bridge", "objection_tool", "verification", "terminal"},
            "api": base | {"caido_tool", "frida_tool", "verification", "terminal"},
            "exploit": base | {"frida_tool", "caido_tool", "device_bridge", "terminal"},
            "flutter": base | {"reflutter_tool", "frida_tool", "apk_tool", "terminal"},
        }
        return role_map.get(self.role, role_map["root"])

    def _role_default_skills(self) -> list[str]:
        role_map = {
            "root": ["root_orchestrator"],
            "static": ["static_analyzer"],
            "dynamic": ["dynamic_tester"],
            "api": ["api_discoverer"],
            "exploit": ["exploit_chainer"],
            "flutter": ["flutter_analysis"],
        }
        return role_map.get(self.role, [])

    def build_system_prompt(self) -> str:
        requested_skills = self._role_default_skills() + list(self.state.skills)
        resolved_skills = resolve_skill_dependencies(requested_skills)
        valid_skills, invalid_skills = validate_skill_names(resolved_skills)
        loaded_skills = load_skills(valid_skills, resolve_dependencies=False)
        skill_warnings = collect_skill_warnings(valid_skills)

        if invalid_skills:
            self.state.add_note(f"invalid_skills: {', '.join(invalid_skills)}")

        template = Template(self._template_path.read_text(encoding="utf-8"))
        return template.render(
            role=self.role,
            is_root=self.role == "root",
            scan_mode=self.scan_mode,
            targets_text=self.targets or [],
            custom_instructions=self.instruction,
            platform=self.state.device_platform,
            device_id=self.state.connected_device,
            target_app=self.state.target_app,
            tools_prompt=get_tools_prompt(include_modules=self._role_modules()),
            loaded_skills=loaded_skills,
            loaded_skill_names=list(loaded_skills.keys()),
            skill_warnings=skill_warnings,
            invalid_skill_names=invalid_skills,
        )

    async def on_scan_complete(self, findings: list[dict[str, Any]]) -> None:
        del findings
        return

    async def execute_scan(self) -> dict[str, Any]:
        await self.initialize()
        return await self.agent_loop()
