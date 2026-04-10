from __future__ import annotations

import re

_INVOKE_OPEN = re.compile(r"<invoke\s+name=\"([^\"]+)\"\s*>", re.IGNORECASE)
_PARAM_OPEN = re.compile(r"<param\s+name=\"([^\"]+)\"\s*>", re.IGNORECASE)
_FUNCTION_RE = re.compile(r"<function=(\w+)>(.*?)</function>", re.DOTALL | re.IGNORECASE)
_PARAMETER_RE = re.compile(r"<parameter=(\w+)>(.*?)</parameter>", re.DOTALL | re.IGNORECASE)

# Matches bare XML tags that look like tool calls: <tool_name attr="val">body</tool_name>
# or self-closing <tool_name></tool_name>
_BARE_TOOL_RE = re.compile(
    r"<([a-z][a-z0-9_]+)(\s+[^>]*)?>(.+?)</\1>",
    re.DOTALL | re.IGNORECASE,
)
# Also match empty-body tags: <tool_name attr="val"></tool_name>
_BARE_TOOL_EMPTY_RE = re.compile(
    r"<([a-z][a-z0-9_]+)(\s+[^>]*)?>\s*</\1>",
    re.DOTALL | re.IGNORECASE,
)
# Matches attribute-style params inside a bare opening tag: key="value"
_ATTR_RE = re.compile(r'(\w+)="([^"]*)"')

# Known tag names that are NOT tool calls (standard XML markup used in prompts/responses)
_NON_TOOL_TAGS = frozenset(
    {
        "function",
        "parameter",
        "invoke",
        "param",
        "tool_result",
        "summary",
        "details",
        "reflection",
        "e",
        "identity",
        "methodology",
        "targets",
        "tools",
        "tool",
        "tool_usage_guidelines",
        "tool_call_format",
        "finding_format",
        "thinking_process",
        "execution_rules",
        "device_capabilities",
        "agent_graph_rules",
        "custom_instructions",
        "root_agent_instructions",
        "specialized_knowledge",
        "invalid_skills",
        "skill_warnings",
        "skill_warning",
        "parameters",
        "description",
    }
)


def _normalize_bare_tool_calls(text: str) -> str:
    """Convert <tool_name key=\"val\">body</tool_name> into <function=tool_name>..."""
    from maya.tools.registry import _tools_by_name  # local import to avoid circular

    def _replace_empty(m: re.Match) -> str:
        tag = m.group(1)
        attrs_str = m.group(2) or ""

        if tag.lower() in _NON_TOOL_TAGS:
            return m.group(0)
        if tag not in _tools_by_name:
            return m.group(0)

        parts = [f"<function={tag}>"]
        for attr_name, attr_val in _ATTR_RE.findall(attrs_str):
            parts.append(f"<parameter={attr_name}>{attr_val}</parameter>")
        parts.append("</function>")
        return "\n".join(parts)

    def _replace_body(m: re.Match) -> str:
        tag = m.group(1)
        attrs_str = m.group(2) or ""
        body = m.group(3).strip()

        if tag.lower() in _NON_TOOL_TAGS:
            return m.group(0)
        if tag not in _tools_by_name:
            return m.group(0)

        parts = [f"<function={tag}>"]

        # Convert attributes to <parameter=...>
        for attr_name, attr_val in _ATTR_RE.findall(attrs_str):
            parts.append(f"<parameter={attr_name}>{attr_val}</parameter>")

        # Convert body <param_name>value</param_name> style to <parameter=...>
        if body:
            inner_tags = re.findall(r"<(\w+)>([^<]*)</\1>", body)
            for param_name, param_val in inner_tags:
                if param_name.lower() not in _NON_TOOL_TAGS:
                    parts.append(f"<parameter={param_name}>{param_val.strip()}</parameter>")

        parts.append("</function>")
        return "\n".join(parts)

    # First handle tags with body content
    result = _BARE_TOOL_RE.sub(_replace_body, text)
    # Then handle empty-body tags (including those with only attributes)
    result = _BARE_TOOL_EMPTY_RE.sub(_replace_empty, result)
    return result


def normalize_tool_format(text: str) -> str:
    # First: normalize <invoke>/<param> variants
    normalized = _INVOKE_OPEN.sub(r"<function=\1>", text)
    normalized = normalized.replace("</invoke>", "</function>")
    normalized = _PARAM_OPEN.sub(r"<parameter=\1>", normalized)
    normalized = normalized.replace("</param>", "</parameter>")
    # Second: normalize bare XML tool tags like <device_list></device_list>
    normalized = _normalize_bare_tool_calls(normalized)
    return normalized


def parse_tool_invocations(text: str) -> list[dict[str, dict[str, str] | str]]:
    invocations: list[dict[str, dict[str, str] | str]] = []
    for tool_name, block in _FUNCTION_RE.findall(text):
        args: dict[str, str] = {}
        for param_name, value in _PARAMETER_RE.findall(block):
            args[param_name] = value.strip()
        invocations.append({"toolName": tool_name, "args": args})
    return invocations


def truncate_result(text: str, limit: int = 10_000) -> str:
    if len(text) <= limit:
        return text
    head = text[:4000]
    tail = text[-4000:]
    dropped = len(text) - 8000
    return f"{head}\n[truncated {dropped} chars]\n{tail}"
