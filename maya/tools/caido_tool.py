from __future__ import annotations

import json
import os
import subprocess
from typing import Any

import requests

from .registry import register_tool

_CAIDO_STATE: dict[str, object] = {
    "pid": None,
    "listen": None,
    "endpoint_map": {},
}

_DEFAULT_CANDIDATES: dict[str, list[tuple[str, str]]] = {
    "search_traffic": [
        ("POST", "/api/http/history/search"),
        ("POST", "/api/history/search"),
    ],
    "replay_request": [
        ("POST", "/api/replay/send"),
        ("POST", "/api/http/replay"),
    ],
    "export_sitemap": [
        ("GET", "/api/sitemap/export"),
        ("GET", "/api/http/sitemap"),
    ],
    "automate_fuzz": [
        ("POST", "/api/automate/fuzz"),
        ("POST", "/api/fuzz/run"),
    ],
    "create_finding": [
        ("POST", "/api/findings/create"),
        ("POST", "/api/finding/create"),
    ],
    "set_scope": [
        ("POST", "/api/scope/set"),
        ("POST", "/api/http/scope"),
    ],
    "get_websocket_traffic": [
        ("POST", "/api/websocket/search"),
        ("POST", "/api/ws/search"),
    ],
}


def _caido_api_base() -> str:
    return os.environ.get("CAIDO_API_BASE", "http://127.0.0.1:8080").rstrip("/")


def _caido_auth_headers() -> dict[str, str]:
    token = os.environ.get("CAIDO_PAT", "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def _load_override_map() -> dict[str, tuple[str, str]]:
    raw = os.environ.get("CAIDO_ENDPOINT_MAP", "").strip()
    if not raw:
        return {}
    data = json.loads(raw)
    out: dict[str, tuple[str, str]] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            out[key] = (str(value.get("method", "GET")).upper(), str(value.get("path", "/")))
        elif isinstance(value, str):
            out[key] = ("GET", value)
    return out


def _probe_endpoint(base: str, method: str, path: str) -> bool:
    headers = _caido_auth_headers()
    url = f"{base}{path}"
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=5)
        else:
            r = requests.options(url, headers=headers, timeout=5)
        return r.status_code < 500
    except Exception:
        return False


def _discover_from_openapi(base: str) -> dict[str, tuple[str, str]]:
    headers = _caido_auth_headers()
    for path in ("/api/openapi.json", "/openapi.json"):
        try:
            r = requests.get(f"{base}{path}", headers=headers, timeout=5)
            if r.status_code != 200:
                continue
            data = r.json()
            paths = data.get("paths", {})
            discovered: dict[str, tuple[str, str]] = {}
            for op, candidates in _DEFAULT_CANDIDATES.items():
                for cand_method, cand_path in candidates:
                    if cand_path in paths and cand_method.lower() in paths[cand_path]:
                        discovered[op] = (cand_method, cand_path)
                        break
            return discovered
        except Exception:  # noqa: S112
            continue
    return {}


def _resolve_endpoint_map(force_refresh: bool = False) -> dict[str, tuple[str, str]]:
    if _CAIDO_STATE.get("endpoint_map") and not force_refresh:
        return _CAIDO_STATE["endpoint_map"]  # type: ignore[return-value]

    base = _caido_api_base()
    endpoint_map: dict[str, tuple[str, str]] = {}

    endpoint_map.update(_load_override_map())
    endpoint_map.update(_discover_from_openapi(base))

    for op, candidates in _DEFAULT_CANDIDATES.items():
        if op in endpoint_map:
            continue
        for method, path in candidates:
            if _probe_endpoint(base, method, path):
                endpoint_map[op] = (method, path)
                break

    _CAIDO_STATE["endpoint_map"] = endpoint_map
    return endpoint_map


def _request(op_name: str, payload: dict[str, Any] | None = None) -> dict:
    base = _caido_api_base()
    endpoint_map = _resolve_endpoint_map()
    mapping = endpoint_map.get(op_name)
    if not mapping:
        return {
            "status": "error",
            "message": f"no verified endpoint for operation: {op_name}",
            "hint": "Run caido_refresh_endpoint_map after Caido is running",
        }

    method, path = mapping
    url = f"{base}{path}"
    headers = _caido_auth_headers()

    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=30)
        else:
            r = requests.post(url, json=payload or {}, headers=headers, timeout=30)
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": str(exc), "url": url}

    if r.status_code >= 400:
        return {"status": "error", "code": r.status_code, "body": r.text, "url": url}

    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text}

    return {"status": "ok", "endpoint": path, "method": method, "result": body}


@register_tool(sandbox_execution=True)
def caido_start(listen: str = "0.0.0.0:8080") -> dict:
    """Start Caido in headless mode and warm endpoint map."""
    cmd = ["caido-cli", "--listen", listen, "--no-open", "--allow-guests"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    _CAIDO_STATE["pid"] = proc.pid
    _CAIDO_STATE["listen"] = listen
    mapping = _resolve_endpoint_map(force_refresh=True)
    return {"status": "ok", "pid": proc.pid, "listen": listen, "endpoint_map": mapping}


@register_tool(sandbox_execution=True)
def caido_refresh_endpoint_map() -> dict:
    """Refresh and return verified Caido endpoint map from running instance."""
    mapping = _resolve_endpoint_map(force_refresh=True)
    return {"status": "ok", "endpoint_map": mapping}


@register_tool(sandbox_execution=True)
def caido_search_traffic(query: str) -> dict:
    """Search traffic using verified endpoint mapping."""
    return _request("search_traffic", payload={"query": query})


@register_tool(sandbox_execution=True)
def caido_replay_request(request_id: str, modifications: str = "{}") -> dict:
    """Replay request with modifications using verified endpoint mapping."""
    return _request(
        "replay_request", payload={"request_id": request_id, "modifications": json.loads(modifications or "{}")}
    )


@register_tool(sandbox_execution=True)
def caido_export_sitemap() -> dict:
    """Export sitemap using verified endpoint mapping."""
    return _request("export_sitemap")


@register_tool(sandbox_execution=True)
def caido_automate_fuzz(endpoint: str, payloads: str = "") -> dict:
    """Run fuzz workflow using verified endpoint mapping."""
    return _request("automate_fuzz", payload={"endpoint": endpoint, "payloads": payloads})


@register_tool(sandbox_execution=True)
def caido_create_finding(title: str, severity: str, description: str) -> dict:
    """Create finding using verified endpoint mapping."""
    return _request("create_finding", payload={"title": title, "severity": severity, "description": description})


@register_tool(sandbox_execution=True)
def caido_set_scope(scope: str) -> dict:
    """Set capture scope using verified endpoint mapping."""
    return _request("set_scope", payload={"scope": scope})


@register_tool(sandbox_execution=True)
def caido_get_websocket_traffic(filter_expr: str = "") -> dict:
    """Retrieve websocket traffic using verified endpoint mapping."""
    return _request("get_websocket_traffic", payload={"filter": filter_expr})


@register_tool(sandbox_execution=True)
def caido_command(method: str, params: str = "{}") -> dict:
    """Send any command to Caido's SDK/API.

    method: the Caido API method or endpoint path (e.g. '/api/intercept/toggle').
    params: JSON string of parameters to send.

    The skill caido_operations.md teaches the agent which methods and params to use.
    """
    base = _caido_api_base()
    headers = _caido_auth_headers()
    try:
        parsed_params = json.loads(params) if isinstance(params, str) else params
    except json.JSONDecodeError:
        return {"status": "error", "message": f"invalid JSON params: {params}"}

    endpoint = method if method.startswith("/") else f"/api/{method}"
    try:
        r = requests.post(f"{base}{endpoint}", json=parsed_params, headers=headers, timeout=30)
        try:
            body = r.json()
        except Exception:
            body = {"raw": r.text}
        return {"status": "ok" if r.status_code < 400 else "error", "code": r.status_code, "result": body}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": str(exc)}
