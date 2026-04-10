from __future__ import annotations

import inspect
from collections import defaultdict
from collections.abc import Callable
from typing import Any

ToolFn = Callable[..., Any]


tools: list[dict[str, Any]] = []
_tools_by_name: dict[str, ToolFn] = {}
_tool_param_schemas: dict[str, dict[str, set[str]]] = {}


def _module_group(func: ToolFn) -> str:
    parts = func.__module__.split(".")
    if len(parts) >= 3:
        return parts[2]
    return "misc"


def _build_schema_from_signature(func: ToolFn) -> dict[str, set[str]]:
    sig = inspect.signature(func)
    required: set[str] = set()
    params: set[str] = set()
    for name, param in sig.parameters.items():
        if name in {"agent_state", "self", "kwargs", "args"}:
            continue
        params.add(name)
        if param.default is inspect.Parameter.empty:
            required.add(name)
    return {"required": required, "params": params}


def register_tool(*, sandbox_execution: bool = True) -> Callable[[ToolFn], ToolFn]:
    def _decorator(func: ToolFn) -> ToolFn:
        name = func.__name__
        module = _module_group(func)
        schema = _build_schema_from_signature(func)
        entry = {
            "name": name,
            "function": func,
            "module": module,
            "sandbox_execution": sandbox_execution,
            "xml_schema": _to_xml_schema(name, func, schema),
        }
        tools.append(entry)
        _tools_by_name[name] = func
        _tool_param_schemas[name] = schema
        return func

    return _decorator


def _to_xml_schema(name: str, func: ToolFn, schema: dict[str, set[str]]) -> str:
    description = (inspect.getdoc(func) or "No description provided").strip()
    lines = [f'<tool name="{name}">', f"  <description>{description}</description>", "  <parameters>"]
    for param_name in sorted(schema["params"]):
        required = "true" if param_name in schema["required"] else "false"
        lines.append(f'    <parameter name="{param_name}" type="string" required="{required}">{param_name}</parameter>')
    lines.extend(["  </parameters>", "</tool>"])
    return "\n".join(lines)


def get_tools_prompt(include_modules: set[str] | None = None) -> str:
    grouped: dict[str, list[str]] = defaultdict(list)
    for entry in tools:
        if include_modules is not None and entry["module"] not in include_modules:
            continue
        grouped[entry["module"]].append(entry["xml_schema"])

    blocks: list[str] = []
    for module in sorted(grouped.keys()):
        blocks.append(f"<{module}_tools>")
        blocks.extend(grouped[module])
        blocks.append(f"</{module}_tools>")
    return "\n".join(blocks)


def get_tool(name: str) -> ToolFn | None:
    return _tools_by_name.get(name)


def get_tool_schema(name: str) -> dict[str, set[str]] | None:
    return _tool_param_schemas.get(name)


def should_execute_in_sandbox(tool_name: str) -> bool:
    for entry in tools:
        if entry["name"] == tool_name:
            return bool(entry["sandbox_execution"])
    return True


def needs_agent_state(func: ToolFn) -> bool:
    return "agent_state" in inspect.signature(func).parameters
