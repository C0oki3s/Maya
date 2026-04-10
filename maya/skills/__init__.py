from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml

_CLI_SKILLS_DIR: Path | None = None
_HIDDEN_SKILL_CATEGORIES = {"scan_modes", "coordination"}
_VERSION_CACHE: dict[str, str] = {}


def set_cli_skills_dir(path: str | None) -> None:
    global _CLI_SKILLS_DIR
    _CLI_SKILLS_DIR = Path(path).expanduser().resolve() if path else None


def _search_paths() -> list[Path]:
    env_dir = os.environ.get("MAYA_SKILLS_DIR")
    env_path = Path(env_dir).expanduser().resolve() if env_dir else None
    user_home = (Path.home() / ".maya" / "skills").resolve()
    project_default = Path(__file__).parent.resolve()

    ordered = [_CLI_SKILLS_DIR, env_path, user_home, project_default]
    return [p for p in ordered if p is not None]


def _collect_files() -> dict[str, dict[str, Path]]:
    merged: dict[str, dict[str, Path]] = {}
    for base in reversed(_search_paths()):
        if not base.exists() or not base.is_dir():
            continue
        for category in base.iterdir():
            if not category.is_dir() or category.name.startswith("_"):
                continue
            for md in category.glob("*.md"):
                merged.setdefault(category.name, {})[md.stem] = md
    return merged


def get_available_skills(include_hidden: bool = False) -> dict[str, list[str]]:
    merged = _collect_files()
    if include_hidden:
        return {k: sorted(v.keys()) for k, v in sorted(merged.items())}
    return {k: sorted(v.keys()) for k, v in sorted(merged.items()) if k not in _HIDDEN_SKILL_CATEGORIES}


def get_all_skill_names(include_hidden: bool = True) -> set[str]:
    out: set[str] = set()
    for _, names in get_available_skills(include_hidden=include_hidden).items():
        out.update(names)
    return out


def validate_skill_names(names: list[str]) -> tuple[list[str], list[str]]:
    all_skills = get_all_skill_names(include_hidden=True)
    valid: list[str] = []
    invalid: list[str] = []
    for name in names:
        if name in all_skills:
            valid.append(name)
        else:
            invalid.append(name)
    return valid, invalid


def _find_skill_path(name: str) -> Path | None:
    merged = _collect_files()

    if "/" in name:
        category, skill_name = name.split("/", 1)
        return merged.get(category, {}).get(skill_name)

    for category in merged.values():
        if name in category:
            return category[name]
    return None


def _strip_frontmatter(content: str) -> str:
    if not content.startswith("---\n"):
        return content

    parts = content.split("\n---\n", 1)
    if len(parts) == 2:
        return parts[1].lstrip()
    return content


def _parse_frontmatter(content: str) -> dict[str, Any]:
    if not content.startswith("---\n"):
        return {}

    parts = content.split("\n---\n", 1)
    if len(parts) != 2:
        return {}

    try:
        data = yaml.safe_load(parts[0].strip("-\n ")) or {}
    except Exception:  # noqa: BLE001
        return {}

    if not isinstance(data, dict):
        return {}
    normalized: dict[str, Any] = {}
    for key, value in data.items():
        normalized[str(key)] = value
    return normalized


def get_skill_frontmatter(name: str) -> dict[str, Any]:
    path = _find_skill_path(name)
    if path is None:
        return {}
    return _parse_frontmatter(path.read_text(encoding="utf-8"))


def resolve_skill_dependencies(skill_names: list[str]) -> list[str]:
    resolved: list[str] = []
    seen: set[str] = set()

    def _visit(skill: str) -> None:
        if skill in seen:
            return
        seen.add(skill)

        metadata = get_skill_frontmatter(skill)
        requires = metadata.get("requires", [])
        if isinstance(requires, str):
            requires = [requires]
        if isinstance(requires, list):
            for dep in requires:
                dep_name = str(dep).strip()
                if dep_name:
                    _visit(dep_name)
        resolved.append(skill)

    for skill_name in skill_names:
        trimmed = skill_name.strip()
        if trimmed:
            _visit(trimmed)

    valid, _ = validate_skill_names(resolved)
    return [name for name in resolved if name in set(valid)]


def _read_tool_version(command: list[str], pattern: str) -> str:
    cache_key = " ".join(command)
    if cache_key in _VERSION_CACHE:
        return _VERSION_CACHE[cache_key]

    try:
        proc = subprocess.run(command, text=True, capture_output=True, timeout=8)
        output = (proc.stdout + "\n" + proc.stderr).strip()
    except Exception:  # noqa: BLE001
        output = ""

    match = re.search(pattern, output)
    version = match.group(1) if match else ""
    _VERSION_CACHE[cache_key] = version
    return version


def collect_skill_warnings(skill_names: list[str]) -> list[str]:
    warnings: list[str] = []
    loaded = resolve_skill_dependencies(skill_names)

    for skill_name in loaded:
        metadata = get_skill_frontmatter(skill_name)
        frida_tested = str(metadata.get("frida_version_tested", "")).strip()
        if frida_tested:
            installed = _read_tool_version(["frida", "--version"], r"(\d+\.\d+(?:\.\d+)?)")
            if installed:
                tested_mm = ".".join(frida_tested.split(".")[:2])
                installed_mm = ".".join(installed.split(".")[:2])
                if tested_mm and installed_mm and tested_mm != installed_mm:
                    warnings.append(
                        f"{skill_name}: tested with Frida {frida_tested},"
                        f" installed {installed}; verify behavior carefully"
                    )
    return warnings


def load_skills(skill_names: list[str], resolve_dependencies: bool = True) -> dict[str, str]:
    names = resolve_skill_dependencies(skill_names) if resolve_dependencies else skill_names
    loaded: dict[str, str] = {}
    for name in names:
        path = _find_skill_path(name)
        if path is None:
            continue
        content = path.read_text(encoding="utf-8")
        loaded[name] = _strip_frontmatter(content)
    return loaded


def list_available_skills_with_sources(include_hidden: bool = False) -> list[dict[str, str]]:
    merged = _collect_files()
    out: list[dict[str, str]] = []
    for category, skills in sorted(merged.items()):
        if not include_hidden and category in _HIDDEN_SKILL_CATEGORIES:
            continue
        for name, path in sorted(skills.items()):
            content = path.read_text(encoding="utf-8")
            frontmatter = _parse_frontmatter(content)
            out.append(
                {
                    "category": category,
                    "skill": name,
                    "description": str(frontmatter.get("description", "")),
                    "source": str(path),
                }
            )
    return out


def generate_skills_description() -> str:
    entries = list_available_skills_with_sources()
    if not entries:
        return "No skills currently available."

    lines = []
    for entry in entries:
        description = f": {entry['description']}" if entry.get("description") else ""
        lines.append(f"- {entry['category']}/{entry['skill']}{description} ({entry['source']})")
    return "\n".join(lines)
