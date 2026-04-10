"""Smart memory system â€” persistent memory across scans with keyword recall."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from time import time

from .registry import register_tool

_MEMORY_DIR = Path(os.environ.get("MAYA_MEMORY_DIR", str(Path.home() / ".maya" / "memory")))


def _ensure_dir() -> Path:
    _MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    return _MEMORY_DIR


def _load_entries() -> list[dict]:
    mem_file = _ensure_dir() / "memory.jsonl"
    if not mem_file.exists():
        return []
    entries: list[dict] = []
    for line in mem_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def _append_entry(entry: dict) -> None:
    mem_file = _ensure_dir() / "memory.jsonl"
    with open(mem_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _save_entries(entries: list[dict]) -> None:
    mem_file = _ensure_dir() / "memory.jsonl"
    with open(mem_file, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")


@register_tool(sandbox_execution=False)
def memory_store(
    key: str,
    value: str,
    category: str = "general",
    tags: str = "",
) -> dict:
    """Save a successful approach, finding, or technique to long-term memory.

    key: short identifier (e.g. 'okhttp4_ssl_bypass').
    value: the knowledge to store.
    category: 'approach', 'finding', 'technique', 'app_specific', 'general'.
    tags: comma-separated tags for search (e.g. 'ssl,okhttp,bypass').
    """
    entry = {
        "key": key,
        "value": value,
        "category": category,
        "tags": [t.strip() for t in tags.split(",") if t.strip()] if tags else [],
        "timestamp": time(),
    }
    _append_entry(entry)
    return {"status": "ok", "entry": entry, "total_entries": len(_load_entries())}


@register_tool(sandbox_execution=False)
def memory_recall(
    query: str = "",
    category: str = "",
    key: str = "",
    limit: str = "10",
) -> dict:
    """Search memory for relevant past experience.

    query: keyword search across keys, values, and tags.
    category: filter by category.
    key: exact key lookup.
    """
    entries = _load_entries()

    matches = [e for e in entries if e.get("key") == key] if key else entries

    if category:
        matches = [e for e in matches if e.get("category") == category]

    if query:
        query_terms = set(re.findall(r"\w+", query.lower()))
        scored: list[tuple[int, dict]] = []
        for entry in matches:
            searchable = f"{entry.get('key', '')} {entry.get('value', '')} {' '.join(entry.get('tags', []))}".lower()
            score = sum(1 for term in query_terms if term in searchable)
            if score > 0:
                scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        matches = [e for _, e in scored[: int(limit)]]
    else:
        matches = matches[-int(limit) :]

    return {
        "status": "ok",
        "query": query,
        "results": matches,
        "result_count": len(matches),
        "total_memories": len(entries),
    }


@register_tool(sandbox_execution=False)
def memory_update(
    key: str,
    new_value: str,
) -> dict:
    """Update an existing memory entry by key.

    If multiple entries share a key, updates the most recent one.
    """
    entries = _load_entries()
    updated = False

    for i in range(len(entries) - 1, -1, -1):
        if entries[i].get("key") == key:
            entries[i]["value"] = new_value
            entries[i]["updated_at"] = time()
            updated = True
            break

    if not updated:
        return {"status": "error", "message": f"no memory found with key: {key}"}

    _save_entries(entries)
    return {"status": "ok", "key": key, "updated": True}
