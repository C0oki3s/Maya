from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ScanConfig:
    targets: list[dict[str, str]] = field(default_factory=list)
    device_id: str | None = None
    platform: str | None = None
    instruction: str = ""
    instruction_file: str | None = None
    scan_mode: str = "quick"
    non_interactive: bool = False
    output_dir: str = "maya_runs/default"
    max_agents: int = 7
    skills_dir: str | None = None
    resume: str | None = None
