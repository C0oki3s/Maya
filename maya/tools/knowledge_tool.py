"""RAG-enhanced vulnerability knowledge â€” semantic search across skills and vuln-db."""

from __future__ import annotations

import os
import re
from pathlib import Path

from .registry import register_tool

_KNOWLEDGE_DIRS: list[Path] = []
_INDEX: list[dict[str, str]] = []
_INDEXED = False


def _get_knowledge_dirs() -> list[Path]:
    dirs = [
        Path(__file__).resolve().parent.parent / "skills",
        Path.home() / ".maya" / "vulndb",
        Path.home() / ".maya" / "knowledge",
    ]
    extra = os.environ.get("MAYA_KNOWLEDGE_DIRS", "")
    if extra:
        dirs.extend(Path(d.strip()) for d in extra.split(",") if d.strip())
    return [d for d in dirs if d.exists()]


def _build_index() -> list[dict[str, str]]:
    """Index all markdown/text files into searchable chunks."""
    global _INDEX, _INDEXED
    if _INDEXED:
        return _INDEX

    _INDEX = []
    for knowledge_dir in _get_knowledge_dirs():
        for md_file in knowledge_dir.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:  # noqa: S112
                continue

            # Chunk by heading
            chunks = re.split(r"(?=^#{1,3}\s)", content, flags=re.MULTILINE)
            for chunk in chunks:
                chunk = chunk.strip()
                if len(chunk) < 20:
                    continue
                # Extract heading
                heading_match = re.match(r"^#{1,3}\s+(.+)", chunk)
                heading = heading_match.group(1).strip() if heading_match else ""
                _INDEX.append(
                    {
                        "file": str(md_file),
                        "heading": heading,
                        "content": chunk[:2000],
                        "tokens": chunk.lower(),
                    }
                )

    _INDEXED = True
    return _INDEX


def _keyword_search(query: str, top_k: int = 5) -> list[dict[str, str]]:
    """Simple keyword-based search with TF scoring."""
    index = _build_index()
    query_terms = set(re.findall(r"\w+", query.lower()))

    scored: list[tuple[float, dict[str, str]]] = []
    for entry in index:
        tokens = entry["tokens"]
        score = sum(1 for term in query_terms if term in tokens)
        # Boost for heading matches
        heading_lower = entry["heading"].lower()
        score += sum(3 for term in query_terms if term in heading_lower)
        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {"file": item["file"], "heading": item["heading"], "content": item["content"], "score": str(score)}
        for score, item in scored[:top_k]
    ]


@register_tool(sandbox_execution=False)
def knowledge_search(query: str, top_k: str = "5") -> dict:
    """Semantic search across all skills and vuln-db files.

    Returns the top matching knowledge chunks for the given query.
    Searches skills/, ~/.maya/vulndb/, and ~/.maya/knowledge/.
    """
    results = _keyword_search(query, top_k=int(top_k))
    return {
        "status": "ok",
        "query": query,
        "results": results,
        "result_count": len(results),
        "indexed_chunks": len(_build_index()),
    }


@register_tool(sandbox_execution=False)
def knowledge_ingest(file_path: str) -> dict:
    """Index a new skill/vuln file into the knowledge base at runtime.

    Adds the file's contents to the searchable index.
    """
    global _INDEXED
    p = Path(file_path)
    if not p.exists():
        return {"status": "error", "message": f"file not found: {file_path}"}

    try:
        content = p.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        return {"status": "error", "message": f"read error: {exc}"}

    chunks = re.split(r"(?=^#{1,3}\s)", content, flags=re.MULTILINE)
    added = 0
    for chunk in chunks:
        chunk = chunk.strip()
        if len(chunk) < 20:
            continue
        heading_match = re.match(r"^#{1,3}\s+(.+)", chunk)
        heading = heading_match.group(1).strip() if heading_match else ""
        _INDEX.append(
            {
                "file": str(p),
                "heading": heading,
                "content": chunk[:2000],
                "tokens": chunk.lower(),
            }
        )
        added += 1

    return {"status": "ok", "file": file_path, "chunks_added": added, "total_index_size": len(_INDEX)}
