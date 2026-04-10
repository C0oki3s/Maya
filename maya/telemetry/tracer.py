from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Tracer:
    run_dir: Path
    events: list[dict[str, Any]] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    api_endpoints: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def log(self, event_type: str, payload: dict[str, Any]) -> None:
        self.events.append({"ts": _now(), "type": event_type, "payload": payload})

    def record_finding(self, finding: dict[str, Any]) -> None:
        self.findings.append(finding)

    def record_api_endpoint(self, endpoint: dict[str, Any]) -> None:
        self.api_endpoints.append(endpoint)

    def persist(self) -> None:
        (self.run_dir / "trace.json").write_text(json.dumps(self.events, indent=2), encoding="utf-8")
        (self.run_dir / "findings.json").write_text(json.dumps(self.findings, indent=2), encoding="utf-8")
        (self.run_dir / "api_endpoints.json").write_text(json.dumps(self.api_endpoints, indent=2), encoding="utf-8")
        self._write_markdown_report()
        self._write_html_report()

    def _write_markdown_report(self) -> None:
        critical = [f for f in self.findings if str(f.get("severity", "")).lower() == "critical"]
        high = [f for f in self.findings if str(f.get("severity", "")).lower() == "high"]
        medium = [f for f in self.findings if str(f.get("severity", "")).lower() == "medium"]
        low = [f for f in self.findings if str(f.get("severity", "")).lower() == "low"]
        info = [f for f in self.findings if str(f.get("severity", "")).lower() == "info"]

        lines = [
            "# Mobile Security Assessment Report",
            "",
            "## Executive Summary",
            (
                f"- Findings: {len(critical)} Critical, {len(high)} High,"
                f" {len(medium)} Medium, {len(low)} Low, {len(info)} Info"
            ),
            "",
            "## Findings",
        ]
        for finding in self.findings:
            lines.append(f"### {finding.get('title', 'Untitled')}")
            lines.append(f"- Severity: {finding.get('severity', 'unknown')}")
            lines.append(f"- Category: {finding.get('category', 'unknown')}")
            lines.append(f"- Description: {finding.get('description', '')}")
            lines.append("")

        lines.append("## API Endpoints")
        for ep in self.api_endpoints:
            lines.append(f"- {ep.get('method', 'GET')} {ep.get('url', '')} ({ep.get('auth_type', 'unknown')})")

        (self.run_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")

    def _write_html_report(self) -> None:
        html = ["<html><head><title>Maya Report</title></head><body>", "<h1>Mobile Security Assessment Report</h1>"]
        html.append("<h2>Findings</h2><ul>")
        for f in self.findings:
            html.append(f"<li><b>{f.get('title', 'Untitled')}</b> [{f.get('severity', 'unknown')}]</li>")
        html.append("</ul><h2>API Endpoints</h2><ul>")
        for ep in self.api_endpoints:
            html.append(f"<li>{ep.get('method', 'GET')} {ep.get('url', '')}</li>")
        html.append("</ul></body></html>")
        (self.run_dir / "report.html").write_text("".join(html), encoding="utf-8")
