from __future__ import annotations

import os

import requests

from .registry import register_tool


def _mobsf_config() -> tuple[str, str]:
    base = os.environ.get("MOBSF_URL", "http://127.0.0.1:8001")
    api_key = os.environ.get("MOBSF_API_KEY", "")
    return base.rstrip("/"), api_key


def _headers(api_key: str) -> dict[str, str]:
    return {"Authorization": api_key}


@register_tool(sandbox_execution=True)
def mobsf_upload_scan(file_path: str) -> dict:
    """Upload app and trigger MobSF scan."""
    base, key = _mobsf_config()
    with open(file_path, "rb") as fh:
        up = requests.post(f"{base}/api/v1/upload", files={"file": fh}, headers=_headers(key), timeout=60)
    up.raise_for_status()
    data = up.json()
    scan = requests.post(
        f"{base}/api/v1/scan",
        data={"hash": data.get("hash"), "scan_type": data.get("scan_type")},
        headers=_headers(key),
        timeout=120,
    )
    scan.raise_for_status()
    return {"upload": data, "scan": scan.json()}


@register_tool(sandbox_execution=True)
def mobsf_get_results(scan_hash: str) -> dict:
    """Fetch MobSF JSON report by hash."""
    base, key = _mobsf_config()
    r = requests.post(f"{base}/api/v1/report_json", data={"hash": scan_hash}, headers=_headers(key), timeout=60)
    r.raise_for_status()
    return r.json()


@register_tool(sandbox_execution=True)
def mobsf_search_code(scan_hash: str, query: str) -> dict:
    """Search decompiled code in MobSF report payload (best-effort)."""
    report = mobsf_get_results(scan_hash)
    matches = []
    needle = query.lower()
    for k, v in report.items():
        if needle in str(v).lower():
            matches.append({"section": k})
    return {"status": "ok", "matches": matches[:100]}
