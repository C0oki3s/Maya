from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from time import time
from typing import Any

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Input, Label, RichLog, Static, Tree
from textual.widgets.tree import TreeNode
from textual.worker import Worker, WorkerState

from maya.telemetry.event_bus import Event, EventBus, EventType

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Maya Design System — Dark Mode Colour Tokens (ui-ux-pro-max aligned)
#
# True black base with high-contrast desaturated accents.
# Semantic colors: blue (primary), green (success), amber (warn), red (danger).
# All text pairs meet WCAG AA (4.5:1) for accessibility.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# -- Surface scale (black base) --
BG_BASE = "#000000"  # true black background
BG_RAISED = "#0a0a0a"  # slightly raised surfaces
BG_HOVER = "#1a1a1a"  # hover state
BG_ACTIVE = "#2a2a2a"  # active/selected state
BORDER = "#333333"  # subtle borders and dividers

# -- Text scale (high contrast on black) --
TEXT_PRIMARY = "#e5e5e5"  # primary text (contrast 18.5:1)
TEXT_SECONDARY = "#b0b0b0"  # secondary text (contrast 9.7:1)
TEXT_TERTIARY = "#808080"  # tertiary labels (contrast 4.6:1 — meets AA)
TEXT_DISABLED = "#555555"  # disabled text

# -- Semantic accent colours (desaturated for dark mode) --
BLUE = "#5a9dff"  # primary accent (contrast 6.5:1)
BLUE_DIM = "#4080cc"  # dimmed blue
GREEN = "#4ade80"  # success (contrast 8.3:1)
GREEN_DIM = "#3ab56d"  # dimmed green
AMBER = "#fbbf24"  # warning (contrast 11.2:1)
AMBER_DIM = "#d9a520"  # dimmed amber
RED = "#f87171"  # danger (contrast 5.9:1)
RED_DIM = "#cc5f5f"  # dimmed red

# -- Special accents --
PURPLE = "#a78bfa"  # API / special category (contrast 6.0:1)
CYAN = "#22d3ee"  # highlight / info (contrast 8.8:1)

# -- Panel-specific tinted backgrounds (subtle on black) --
PANEL_SCAN = "#0a1420"  # blue tint
PANEL_AGENTS = "#091c14"  # green tint
PANEL_TOOLS = "#1f1a0a"  # amber tint
PANEL_SKILLS = "#0a1420"  # blue tint
PANEL_FINDINGS = "#200a0a"  # red tint

# -- Legacy / Compatibility Aliases --
INK = TEXT_PRIMARY
INK2 = TEXT_SECONDARY
INK3 = TEXT_TERTIARY
INK4 = TEXT_DISABLED
PAPER = BG_BASE
PAPER2 = BG_RAISED
PAPER3 = BG_HOVER
RULE = BORDER
BLUE_LT = PANEL_SCAN
GREEN_LT = PANEL_AGENTS
AMBER_LT = PANEL_TOOLS
RED_LT = PANEL_FINDINGS
COVER_BG = BG_BASE
TEAL = CYAN

SURF_LOWEST = BG_RAISED
SURF = BG_BASE
SURF_LOW = BG_RAISED
SURF_MID = BG_HOVER
SURF_HIGH = BG_ACTIVE
SURF_HIGHEST = BG_ACTIVE

ON_SURF = TEXT_SECONDARY
ON_SURF_DIM = TEXT_TERTIARY
ON_SURF_HI = TEXT_PRIMARY

PRIMARY = BLUE
PRIMARY_DIM = BLUE_DIM
SECONDARY = GREEN
ERROR = RED
ERROR_DIM = RED_DIM
WARNING = AMBER
OUTLINE_V = BORDER

# Agent role colors (high contrast variants)
ROLE_COLORS = {
    "root": BLUE,
    "static": GREEN,
    "dynamic": AMBER,
    "api": PURPLE,
    "exploit": RED,
    "flutter": CYAN,
}

# Tool category metadata
TOOL_CATEGORIES = {
    "apk_tool": ("APK / Reverse Eng", 9),
    "caido_tool": ("Caido Proxy", 11),
    "device_bridge": ("Device Bridge", 14),
    "drozer_tool": ("Drozer", 30),
    "frida_tool": ("Frida", 3),
    "mobsf_tool": ("MobSF", 3),
    "objection_tool": ("Objection", 2),
    "reflutter_tool": ("ReFlutter", 3),
    "compliance_tool": ("Compliance", 3),
    "terminal": ("Terminal / Exec", 6),
    "reporting": ("Reporting", 7),
    "agents_graph": ("Agent Mgmt", 3),
    "skills_runtime": ("Skills Runtime", 5),
    "knowledge_tool": ("Knowledge", 2),
    "memory_tool": ("Memory", 3),
    "shared_context": ("Shared Context", 2),
    "verification": ("Verification", 4),
}

# Skill categories
SKILL_CATEGORIES = {
    "agents": ["root_orchestrator", "static_analyzer", "dynamic_tester", "api_discoverer", "exploit_chainer"],
    "platforms": ["android_internals", "ios_internals", "ios_testing"],
    "frameworks": ["flutter_analysis", "react_native_analysis", "xamarin_analysis"],
    "tools": ["frida_operations", "caido_operations", "adb_operations", "objection_operations", "mobsf_operations"],
    "vulnerabilities": [
        "ssl_pinning_bypass",
        "webview_attacks",
        "insecure_storage",
        "auth_bypass",
        "api_security",
        "ipc_vulnerabilities",
    ],
}

# Subagent role definitions
SUBAGENT_ROLES = {
    "root": "Orchestrator — coordinates all agents",
    "static": "Static Analysis — APK/IPA decompilation",
    "dynamic": "Dynamic Testing — runtime instrumentation",
    "api": "API Discovery — endpoint & traffic analysis",
    "exploit": "Exploit Chains — vulnerability chaining",
    "flutter": "Flutter — Dart/Flutter-specific analysis",
}

SEV = {
    "critical": f"bold {RED}",
    "high": RED,
    "medium": AMBER,
    "low": GREEN,
    "info": TEXT_TERTIARY,
}


def _ec(et: EventType) -> str:
    return {
        EventType.AGENT_STARTED: f"bold {PRIMARY}",
        EventType.AGENT_COMPLETED: f"bold {PRIMARY_DIM}",
        EventType.AGENT_FAILED: f"bold {ERROR}",
        EventType.AGENT_SPAWNED: PRIMARY,
        EventType.ITERATION_START: ON_SURF_DIM,
        EventType.ITERATION_END: ON_SURF_DIM,
        EventType.LLM_REQUEST: SECONDARY,
        EventType.LLM_RESPONSE: SECONDARY,
        EventType.LLM_ERROR: ERROR,
        EventType.TOOL_CALL_START: WARNING,
        EventType.TOOL_CALL_COMPLETE: PRIMARY_DIM,
        EventType.TOOL_CALL_ERROR: f"bold {ERROR}",
        EventType.THINKING: ON_SURF,
        EventType.REFLECTION: f"italic {ON_SURF_DIM}",
        EventType.FINDING_ADDED: f"bold {ERROR}",
        EventType.USER_MESSAGE: f"bold {ON_SURF_HI}",
        EventType.SCAN_STARTED: f"bold {PRIMARY}",
        EventType.SCAN_COMPLETED: f"bold {PRIMARY}",
        EventType.CHECKPOINT_SAVED: WARNING,
    }.get(et, ON_SURF)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# QuitModal
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class QuitModal(ModalScreen[bool]):
    CSS = f"""
    QuitModal {{
        align: center middle;
        background: rgba(12, 14, 18, 0.75);
    }}
    #qm-card {{
        width: 38;
        height: 7;
        background: {SURF_HIGHEST};
        padding: 1 2;
        border: none;
    }}
    #qm-title {{
        width: 100%;
        text-align: center;
        color: {ON_SURF_HI};
        margin-bottom: 1;
    }}
    #qm-row {{
        align: center middle;
        width: 100%;
        height: 1;
    }}
    .qm-btn {{
        min-width: 12;
        margin: 0 1;
        border: none;
    }}
    #qm-yes {{
        background: {ERROR_DIM};
        color: {ON_SURF_HI};
    }}
    #qm-yes:hover {{
        background: {ERROR};
    }}
    #qm-no {{
        background: {SURF_HIGH};
        color: {ON_SURF};
    }}
    #qm-no:hover {{
        background: {SURF_HIGHEST};
        color: {ON_SURF_HI};
    }}
    """
    BINDINGS = [
        Binding("y", "yes", show=False),
        Binding("n", "no", show=False),
        Binding("escape", "no", show=False),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="qm-card"):
            yield Label("quit maya?", id="qm-title")
            with Horizontal(id="qm-row"):
                yield Button("yes", id="qm-yes", classes="qm-btn")
                yield Button("no", id="qm-no", classes="qm-btn")

    @on(Button.Pressed, "#qm-yes")
    def _yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#qm-no")
    def _no(self) -> None:
        self.dismiss(False)

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FindingDetail — Center overlay
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class FindingDetail(Static):
    DEFAULT_CSS = f"""
    FindingDetail {{
        width: 100%;
        height: 100%;
        background: {SURF_LOW};
        padding: 2 3;
        color: {ON_SURF};
    }}
    """

    def __init__(self, finding: dict, **kw: Any) -> None:
        super().__init__(**kw)
        self._f = finding

    def render(self) -> str:
        f = self._f
        sev = f.get("severity", "info").upper()
        sc = SEV.get(f.get("severity", "info").lower(), ON_SURF)
        title = f.get("title", "Untitled")
        desc = f.get("description", "—")
        evidence = f.get("evidence", "")
        remediation = f.get("remediation", "")
        agent = f.get("agent_name", "—")
        lines = [
            "",
            f"  [{sc}]{sev}[/]",
            f"  [{ON_SURF_HI}]{title}[/]",
            "",
            f"  [{ON_SURF_DIM}]agent[/]    [{ON_SURF}]{agent}[/]",
            "",
            f"  [{ON_SURF_DIM}]description[/]",
            f"  [{ON_SURF}]{desc}[/]",
        ]
        if evidence:
            lines += ["", f"  [{ON_SURF_DIM}]evidence[/]", f"  [{ON_SURF}]{evidence}[/]"]
        if remediation:
            lines += ["", f"  [{ON_SURF_DIM}]remediation[/]", f"  [{ON_SURF}]{remediation}[/]"]
        lines += ["", "", f"  [{ON_SURF_DIM}]esc to close[/]"]
        return "\n".join(lines)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SidebarStats — tokens / cost / findings
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SidebarStats(Static):
    tokens: reactive[int] = reactive(0)
    cost: reactive[float] = reactive(0.0)
    findings_count: reactive[int] = reactive(0)

    DEFAULT_CSS = f"""
    SidebarStats {{
        height: 3;
        padding: 0 2;
        background: {SURF_LOWEST};
        color: {ON_SURF_DIM};
    }}
    """

    def render(self) -> str:
        c = f"${self.cost:.4f}" if self.cost < 1 else f"${self.cost:.2f}"
        fc = ERROR if self.findings_count else ON_SURF_DIM
        return (
            f"[{ON_SURF_DIM}]tokens  [{PRIMARY_DIM}]{self.tokens:,}[/]\n"
            f"[{ON_SURF_DIM}]cost    [{WARNING}]{c}[/]\n"
            f"[{ON_SURF_DIM}]vulns   [{fc}]{self.findings_count}[/]"
        )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pulse — Breathing accent dot
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class Pulse(Static):
    _tick: reactive[int] = reactive(0)
    DEFAULT_CSS = f"""
    Pulse {{
        width: 3;
        height: 1;
        background: {SURF};
    }}
    """

    def on_mount(self) -> None:
        self.set_interval(1.4, self._beat)

    def _beat(self) -> None:
        self._tick += 1

    def render(self) -> str:
        c = PRIMARY if self._tick % 2 == 0 else PRIMARY_DIM
        g = "●" if self._tick % 2 == 0 else "○"
        return f"[{c}] {g} [/]"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MayaUI — Maya Design System
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class MayaUI(App):
    """Maya — Dark mode design system (ui-ux-pro-max aligned).

    True black background with high-contrast desaturated accents.
    Semantic colors: blue (primary), green (success), amber (warning), red (danger).
    All text meets WCAG AA (4.5:1 minimum contrast).
    """

    CSS = f"""
    Screen {{
        layout: horizontal;
        background: {SURF};
    }}

    /* ── Main: log area ── */
    #main {{
        width: 1fr;
        height: 100%;
        background: {SURF};
    }}

    #bar {{
        height: 1;
        background: {SURF};
        color: {ON_SURF_DIM};
        padding: 0 1;
        dock: top;
    }}

    #log {{
        background: {SURF_LOWEST};
        color: {ON_SURF};
        height: 1fr;
        padding: 1 2;
        scrollbar-size: 1 1;
    }}

    #detail-overlay {{
        display: none;
        height: 1fr;
    }}

    #chat-well {{
        height: 3;
        background: {SURF_LOW};
        padding: 0 2;
        dock: bottom;
    }}
    /* Input: clean, bottom-edge feel */
    #chat {{
        width: 1fr;
        background: {SURF_MID};
        color: {ON_SURF};
        border: none;
    }}
    #chat:focus {{
        background: {SURF_HIGH};
        border: none;
    }}

    /* ── Sidebar: scrollable panel stack ──────────────────────── */
    #sidebar {{
        width: 40;
        height: 100%;
        background: {SURF_LOW};
        border: none;
        padding: 0;
    }}

    #sb-scroll {{
        height: 1fr;
        scrollbar-size: 1 1;
    }}

    /* ── Scan Info panel — deep navy ─────────────────────────── */
    .panel-header {{
        height: 1;
        padding: 0 2;
    }}
    #sb-scan-hdr {{
        color: {SECONDARY};
        background: {PANEL_SCAN};
    }}
    #scan-info {{
        background: {PANEL_SCAN};
        color: {ON_SURF};
        padding: 0 2;
        height: auto;
        max-height: 8;
    }}

    /* ── Agents panel — dark forest ──────────────────────────── */
    #sb-al {{
        height: 1;
        padding: 0 2;
        color: {PRIMARY};
        background: {PANEL_AGENTS};
    }}
    #agents {{
        height: auto;
        min-height: 3;
        max-height: 10;
        background: {PANEL_AGENTS};
        color: {ON_SURF};
        padding: 0 2;
        scrollbar-size: 1 1;
        border: none;
    }}

    /* ── Subagents panel — forest accent ─────────────────────── */
    #sb-sub-hdr {{
        color: {PRIMARY_DIM};
        background: {PANEL_AGENTS};
    }}
    #subagents-info {{
        background: {PANEL_AGENTS};
        color: {ON_SURF};
        padding: 0 2;
        height: auto;
        max-height: 10;
    }}

    /* ── Tools panel — dark plum ─────────────────────────────── */
    #sb-tools-hdr {{
        color: {WARNING};
        background: {PANEL_TOOLS};
    }}
    #tools-tree {{
        height: auto;
        min-height: 3;
        max-height: 12;
        background: {PANEL_TOOLS};
        color: {ON_SURF};
        padding: 0 2;
        scrollbar-size: 1 1;
        border: none;
    }}

    /* ── Skills panel — dark steel ───────────────────────────── */
    #sb-skills-hdr {{
        color: {BLUE};
        background: {PANEL_SKILLS};
    }}
    #skills-tree {{
        height: auto;
        min-height: 3;
        max-height: 10;
        background: {PANEL_SKILLS};
        color: {ON_SURF};
        padding: 0 2;
        scrollbar-size: 1 1;
        border: none;
    }}

    /* Separator */
    .ghost-sep {{
        height: 1;
        background: {OUTLINE_V};
        margin: 0 2;
    }}

    /* ── Findings panel — dark wine ──────────────────────────── */
    #sb-fl {{
        height: 1;
        padding: 0 2;
        color: {ERROR};
        background: {PANEL_FINDINGS};
    }}
    #findings {{
        height: auto;
        min-height: 3;
        max-height: 12;
        background: {PANEL_FINDINGS};
        color: {ON_SURF};
        padding: 0 2;
        scrollbar-size: 1 1;
        border: none;
    }}

    #stats {{
        dock: bottom;
    }}

    Footer {{
        background: {SURF_LOWEST};
        color: {ON_SURF_DIM};
    }}
    """

    BINDINGS = [
        Binding("ctrl+c", "request_quit", "Quit", show=True, priority=True),
        Binding("ctrl+x", "request_quit", "Quit", show=False, priority=True),
        Binding("ctrl+q", "request_quit", "Quit", show=False),
        Binding("tab", "cycle_agent", "Next", show=True),
        Binding("escape", "close_detail", "Back", show=False),
        Binding("ctrl+e", "nudge_enum", "Enum", show=True),
        Binding("ctrl+l", "nudge_flow", "Flow", show=True),
    ]

    def __init__(
        self,
        scan_task: Any = None,
        run_dir: Path | None = None,
        scan_config: dict[str, Any] | None = None,
        scan_worker: Any = None,
        on_user_input: Any = None,
        **kw: Any,
    ) -> None:
        super().__init__(**kw)
        self._scan_task = scan_task
        self._run_dir = run_dir
        self._scan_config = scan_config or {}
        self._scan_worker_fn = scan_worker
        self._on_user_input = on_user_input
        self._agent_ids: list[str] = []
        self._agent_names: dict[str, str] = {}
        self._selected_agent: str | None = None
        self._agent_events: dict[str, list[Event]] = {}
        self._tree_nodes: dict[str, TreeNode[str]] = {}
        self._findings: list[dict] = []
        self._detail_open = False
        self._stage = "idle"
        self._event_count = 0
        self._last_event_at = time()
        self._last_progress_at = time()
        self._last_recovery_at = 0.0
        self._wd_running = False
        self._seen_ckpt: set[str] = set()
        self._tool_calls: dict[str, int] = {}

    # ── Compose ───────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        with Vertical(id="main"):
            with Horizontal(id="bar"):
                yield Pulse()
                yield Static("", id="stage-lbl")
            yield RichLog(id="log", highlight=True, markup=True, wrap=True)
            yield Container(id="detail-overlay")
            with Container(id="chat-well"):
                yield Input(placeholder=" Type to send instructions to the agent...", id="chat")

        with Vertical(id="sidebar"):
            with VerticalScroll(id="sb-scroll"):
                # ── Scan Info ──
                yield Static(" ◈ scan", id="sb-scan-hdr", classes="panel-header")
                yield Static("", id="scan-info")
                yield Static("", classes="ghost-sep")
                # ── Agents ──
                yield Static(" ▲ agents", id="sb-al", classes="panel-header")
                yield Tree("maya", id="agents")
                yield Static("", classes="ghost-sep")
                # ── Findings ──
                yield Static(" ◆ findings", id="sb-fl", classes="panel-header")
                yield Tree("vulns", id="findings")
            yield SidebarStats(id="stats")

        yield Footer()

    # ── Mount ─────────────────────────────────────────────────────

    def on_mount(self) -> None:
        EventBus.instance().subscribe(self._on_event)
        self.query_one("#agents", Tree).root.expand()
        self.query_one("#findings", Tree).root.expand()
        self.query_one("#log", RichLog).write(f"[{PRIMARY_DIM}]maya[/]  [{ON_SURF_DIM}]ready[/]")
        self.set_interval(10.0, self._wd_tick)
        if self._run_dir:
            self.set_interval(3.0, self._ckpt_tick)
        self._populate_scan_info()
        if self._scan_worker_fn is not None:
            self.run_worker(
                self._run_scan_wrapper,
                exclusive=True,
                thread=False,
                exit_on_error=False,
            )

    # ── Scan worker wrapper ────────────────────────────────────────

    async def _run_scan_wrapper(self) -> None:
        try:
            await self._scan_worker_fn()
        except Exception as exc:
            import traceback

            tb = traceback.format_exc()
            try:
                log: RichLog = self.query_one("#log", RichLog)
                log.write(f"[{ERROR}]\u2717  scan crashed: {exc}[/]")
                for line in tb.strip().splitlines()[-8:]:
                    log.write(f"[{ON_SURF_DIM}]  {line}[/]")
            except NoMatches:
                pass
            try:  # noqa: SIM105
                await EventBus.instance().emit(
                    Event(
                        type=EventType.AGENT_FAILED,
                        agent_id="root",
                        agent_name="root",
                        data={"error": str(exc)},
                    )
                )
            except Exception:  # noqa: S110
                pass  # event bus failure must not mask original error

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state == WorkerState.ERROR and event.worker.error:
            try:
                log: RichLog = self.query_one("#log", RichLog)
                log.write(f"[{ERROR}]\u2717  worker error: {event.worker.error}[/]")
            except NoMatches:
                pass

    # ── Populate sidebar panels ───────────────────────────────────

    def _populate_scan_info(self) -> None:
        try:
            panel = self.query_one("#scan-info", Static)
        except NoMatches:
            return
        cfg = self._scan_config
        target = cfg.get("target", "—")
        pkg = cfg.get("package", "—")
        device = cfg.get("device", "—")
        platform = cfg.get("platform", "—")
        model = cfg.get("model", os.environ.get("MAYA_LLM", "—"))
        mode = cfg.get("scan_mode", "—")
        lines = [
            f"  [{ON_SURF_DIM}]target  [{ON_SURF}]{target}[/]",
            f"  [{ON_SURF_DIM}]pkg     [{SECONDARY}]{pkg}[/]",
            f"  [{ON_SURF_DIM}]device  [{PRIMARY_DIM}]{device}[/]",
            f"  [{ON_SURF_DIM}]plat    [{ON_SURF}]{platform}[/]",
            f"  [{ON_SURF_DIM}]model   [{WARNING}]{model}[/]",
            f"  [{ON_SURF_DIM}]mode    [{PRIMARY}]{mode}[/]",
        ]
        panel.update("\n".join(lines))

    def _populate_subagents(self) -> None:
        try:
            panel = self.query_one("#subagents-info", Static)
        except NoMatches:
            return
        lines = []
        for role, desc in SUBAGENT_ROLES.items():
            rc = ROLE_COLORS.get(role, ON_SURF)
            lines.append(f"  [{rc}]● {role:<8}[/] [{ON_SURF_DIM}]{desc}[/]")
        panel.update("\n".join(lines))

    def _populate_tools(self) -> None:
        try:
            tree: Tree[str] = self.query_one("#tools-tree", Tree)
        except NoMatches:
            return
        tree.root.expand()
        total = 0
        for cat_id, (label, count) in TOOL_CATEGORIES.items():
            total += count
            tree.root.add_leaf(
                f"[{WARNING}]{label}[/] [{ON_SURF_DIM}]({count})[/]",
                data=cat_id,
            )
        tree.root.label = f"[{WARNING}]{total} tools[/]"

    def _populate_skills(self) -> None:
        try:
            tree: Tree[str] = self.query_one("#skills-tree", Tree)
        except NoMatches:
            return
        tree.root.expand()
        total = 0
        for cat, skills_list in SKILL_CATEGORIES.items():
            total += len(skills_list)
            node = tree.root.add(f"[{BLUE}]{cat}[/] [{ON_SURF_DIM}]({len(skills_list)})[/]", data=cat)
            for sk in skills_list:
                node.add_leaf(f"[{ON_SURF_DIM}]{sk}[/]", data=sk)
        tree.root.label = f"[{BLUE}]{total}+ skills[/]"

    # ── Quit ──────────────────────────────────────────────────────

    def action_request_quit(self) -> None:
        self.push_screen(QuitModal(), callback=lambda r: self.exit() if r else None)

    # ── Event dispatch ────────────────────────────────────────────

    async def _on_event(self, event: Event) -> None:
        self._event_count += 1
        self._last_event_at = time()
        self._stage = self._infer_stage(event)

        if event.type in {
            EventType.TOOL_CALL_COMPLETE,
            EventType.FINDING_ADDED,
            EventType.AGENT_SPAWNED,
            EventType.CHECKPOINT_SAVED,
        }:
            self._last_progress_at = time()

        self._agent_events.setdefault(event.agent_id, []).append(event)

        if event.agent_id not in self._agent_ids:
            self._agent_ids.append(event.agent_id)
            self._agent_names[event.agent_id] = event.agent_name
            if self._selected_agent is None:
                self._selected_agent = event.agent_id

        self._update_tree(event)
        self._update_stats(event)
        self._update_bar()
        if not self._detail_open:
            self._write_log(event)
        if event.type == EventType.FINDING_ADDED:
            self._add_finding(event)

    # ── Bar ───────────────────────────────────────────────────────

    def _update_bar(self) -> None:
        try:
            lbl = self.query_one("#stage-lbl", Static)
        except NoMatches:
            return
        a = self._agent_names.get(self._selected_agent or "", "maya")
        lbl.update(f" [{ON_SURF}]{a}[/]  [{ON_SURF_DIM}]{self._stage}[/]  [{ON_SURF_DIM}]{self._event_count} evt[/]")

    # ── Stats ─────────────────────────────────────────────────────

    def _update_stats(self, event: Event) -> None:
        try:
            s: SidebarStats = self.query_one("#stats", SidebarStats)
        except NoMatches:
            return
        d = event.data
        if event.type == EventType.LLM_RESPONSE:
            s.tokens = d.get("total_tokens", s.tokens)
            s.cost = d.get("total_cost_usd", s.cost)
        elif event.type == EventType.FINDING_ADDED:
            s.findings_count = len(self._findings) + 1
        if event.type == EventType.TOOL_CALL_START:
            tool = d.get("tool", "?")
            self._tool_calls[tool] = self._tool_calls.get(tool, 0) + 1

    # ── Agent tree ────

    def _update_tree(self, event: Event) -> None:
        try:
            tree: Tree[str] = self.query_one("#agents", Tree)
        except NoMatches:
            return
        if event.agent_id not in self._tree_nodes:
            short = event.agent_id[:6]
            label = f"[{ON_SURF}]{event.agent_name}[/] [{ON_SURF_DIM}]{short}[/]"
            pid = event.data.get("parent_id") if event.type == EventType.AGENT_SPAWNED else None
            parent = self._tree_nodes.get(pid, tree.root) if pid else tree.root
            self._tree_nodes[event.agent_id] = parent.add(label, data=event.agent_id)
            self._tree_nodes[event.agent_id].expand()

        node = self._tree_nodes.get(event.agent_id)
        if not node:
            return
        if event.type == EventType.AGENT_COMPLETED:
            ic, icon = PRIMARY_DIM, "✓"
        elif event.type == EventType.AGENT_FAILED:
            ic, icon = ERROR_DIM, "✗"
        else:
            ic, icon = ON_SURF_DIM, "›"
        node.label = f"[{ic}]{icon}[/] [{ON_SURF}]{event.agent_name}[/] [{ON_SURF_DIM}]{event.agent_id[:6]}[/]"

    # ── Process log ────

    def _write_log(self, event: Event) -> None:
        try:
            log: RichLog = self.query_one("#log", RichLog)
        except NoMatches:
            return

        c = _ec(event.type)
        d = event.data
        et = event.type

        if et == EventType.AGENT_STARTED:
            log.write(f"[{c}]→ {event.agent_name}[/] [{ON_SURF_DIM}]started[/]")
            task = d.get("task", "")[:200]
            if task:
                log.write(f"  [{ON_SURF}]{task}[/]")
        elif et == EventType.AGENT_SPAWNED:
            reason = d.get('reason', '')
            log.write(f"[{c}]+ {event.agent_name}[/] [{ON_SURF_DIM}]spawned[/]")
            if reason:
                log.write(f"  [{ON_SURF_DIM}]▸ {reason[:200]}[/]")
        elif et == EventType.ITERATION_START:
            log.write(f"[{ON_SURF_DIM}]·  iter {d.get('iteration', '?')}[/]")
        elif et == EventType.LLM_RESPONSE:
            model = d.get("model", "?")
            u = d.get("usage", {})
            tok = u.get("total_tokens") or u.get("prompt_tokens", 0) + u.get("completion_tokens", 0)
            log.write(f"[{c}]↓  {model}  {tok}[/]")
        elif et == EventType.THINKING:
            txt = d.get("content", "")[:400]
            if txt:
                log.write(f"[{PRIMARY_DIM}]◆ {event.agent_name}[/] [{ON_SURF}]thinking:[/]")
                log.write(f"  [{ON_SURF_DIM}]{txt}[/]")
        elif et == EventType.TOOL_CALL_START:
            tool_name = d.get('tool', '?')
            reason = d.get('reasoning', '')
            log.write(f"[{c}]▸  {tool_name}[/]")
            if reason:
                log.write(f"  [{ON_SURF_DIM}]{reason[:200]}[/]")
        elif et == EventType.TOOL_CALL_COMPLETE:
            log.write(f"[{c}]✓  {d.get('tool', '?')}[/]  [{ON_SURF_DIM}]{d.get('duration', 0)}s[/]")
        elif et == EventType.TOOL_CALL_ERROR:
            log.write(f"[{c}]✗  {d.get('tool', '?')}[/]  [{ON_SURF_DIM}]{str(d.get('error', ''))[:140]}[/]")
        elif et == EventType.FINDING_ADDED:
            sev = d.get("severity", "info")
            sc = SEV.get(sev.lower(), ON_SURF)
            log.write(f"[{sc}]◆  {sev.upper()}  {d.get('title', '—')}[/]")
        elif et == EventType.AGENT_COMPLETED:
            findings_count = d.get('findings', 0)
            summary = d.get('summary', '')
            log.write(f"[{c}]✓  {event.agent_name}[/] [{GREEN}]completed[/] [{ON_SURF_DIM}]{findings_count} findings[/]")
            if summary:
                log.write(f"  [{ON_SURF}]▸ {summary[:300]}[/]")
        elif et == EventType.AGENT_FAILED:
            log.write(f"[{c}]✗  {event.agent_name}[/]  [{ON_SURF_DIM}]{str(d.get('error', ''))[:140]}[/]")
        elif et == EventType.CHECKPOINT_SAVED:
            log.write(f"[{c}]⟐  ckpt {d.get('iteration', '?')}[/]")
        elif et == EventType.SCAN_COMPLETED:
            log.write(f"[{c}]scan complete[/]")

    # ── Findings sidebar ──────────────────────────────────────────

    def _add_finding(self, event: Event) -> None:
        d = event.data
        finding = {**d, "agent_name": event.agent_name}
        self._findings.append(finding)
        try:
            ftree: Tree[dict] = self.query_one("#findings", Tree)
        except NoMatches:
            return
        sev = d.get("severity", "info").upper()
        title = d.get("title", "Untitled")
        sc = SEV.get(d.get("severity", "info").lower(), ON_SURF)
        ftree.root.add_leaf(f"[{sc}]{sev}[/]  [{ON_SURF}]{title}[/]", data=finding)

    # ── Detail overlay ────────────────────────────────────────────

    @on(Tree.NodeSelected, "#findings")
    def _on_finding_click(self, event: Tree.NodeSelected[dict]) -> None:
        if event.node.data is None or not isinstance(event.node.data, dict):
            return
        self._detail_open = True
        overlay = self.query_one("#detail-overlay", Container)
        log = self.query_one("#log", RichLog)
        log.display = False
        overlay.display = True
        overlay.remove_children()
        overlay.mount(FindingDetail(event.node.data))

    def action_close_detail(self) -> None:
        if not self._detail_open:
            return
        self._detail_open = False
        self.query_one("#detail-overlay", Container).display = False
        self.query_one("#detail-overlay", Container).remove_children()
        self.query_one("#log", RichLog).display = True

    def on_click(self) -> None:
        if self._detail_open:
            self.action_close_detail()

    # ── Agent selection ───────────────────────────────────────────

    @on(Tree.NodeSelected, "#agents")
    def _on_agent_click(self, event: Tree.NodeSelected[str]) -> None:
        if event.node.data and event.node.data in self._agent_ids:
            self._selected_agent = event.node.data
            self._update_bar()

    def action_cycle_agent(self) -> None:
        if not self._agent_ids:
            return
        if self._selected_agent is None:
            self._selected_agent = self._agent_ids[0]
        else:
            i = self._agent_ids.index(self._selected_agent)
            self._selected_agent = self._agent_ids[(i + 1) % len(self._agent_ids)]
        self._update_bar()

    # ── Chat ──────────────────────────────────────────────────────

    @on(Input.Submitted, "#chat")
    async def _on_chat(self, ev: Input.Submitted) -> None:
        text = ev.value.strip()
        if not text:
            return
        ev.input.value = ""
        self.query_one("#log", RichLog).write(f"[{ON_SURF_HI}]▹  {text}[/]")
        await EventBus.instance().emit(
            Event(
                type=EventType.USER_MESSAGE,
                agent_id=self._selected_agent or "user",
                agent_name="user",
                data={"message": text},
            )
        )
        if self._on_user_input is not None:
            await self._on_user_input(text, self._selected_agent)

    # ── Nudges ────────────────────────────────────────────────────

    async def action_nudge_enum(self) -> None:
        if not self._on_user_input or not self._agent_ids:
            return
        t = self._selected_agent or self._agent_ids[0]
        await self._on_user_input(
            "Operator nudge: prioritize enumeration and attack-surface mapping. "
            "List unresolved surfaces, execute targeted tools, checkpoint.",
            t,
        )
        self.query_one("#log", RichLog).write(f"[{ON_SURF_DIM}]nudge → enum[/]")

    async def action_nudge_flow(self) -> None:
        if not self._on_user_input or not self._agent_ids:
            return
        t = self._selected_agent or self._agent_ids[0]
        await self._on_user_input(self._recovery_prompt(), t)
        self.query_one("#log", RichLog).write(f"[{ON_SURF_DIM}]nudge → flow[/]")

    # ── Watchdog ──────────────────────────────────────────────────

    def _wd_tick(self) -> None:
        if self._wd_running:
            return
        self._wd_running = True
        asyncio.create_task(self._wd_check())

    async def _wd_check(self) -> None:
        try:
            if not self._on_user_input or not self._agent_ids:
                return
            now = time()
            stall = now - self._last_progress_at
            if stall < 45 or now - self._last_recovery_at < 90:
                return
            t = self._agent_ids[0]
            await self._on_user_input(self._recovery_prompt(), t)
            self._last_recovery_at = now
            try:  # noqa: SIM105
                self.query_one("#log", RichLog).write(f"[{ON_SURF_DIM}]auto-recovery  stall={int(stall)}s[/]")
            except NoMatches:
                pass
            await EventBus.instance().emit(
                Event(
                    type=EventType.REFLECTION,
                    agent_id=t,
                    agent_name=self._agent_names.get(t, "root"),
                    data={"source": "ui_watchdog", "stage": self._stage, "stall_seconds": int(stall)},
                )
            )
        finally:
            self._wd_running = False

    # ── Checkpoint polling ────────────────────────────────────────

    def _ckpt_tick(self) -> None:
        if not self._run_dir:
            return
        ckdir = self._run_dir / "checkpoints"
        if not ckdir.exists():
            return
        for p in sorted(ckdir.glob("*.json"), key=lambda x: x.stat().st_mtime):
            k = str(p)
            if k in self._seen_ckpt:
                continue
            self._seen_ckpt.add(k)
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                it = int(data.get("iteration_count", 0))
                fc = len(data.get("findings", []))
                ag = data.get("agent_name", "?")
                self.query_one("#log", RichLog).write(f"[{WARNING}]⟐  {ag}  iter={it}  findings={fc}[/]")
            except Exception:  # noqa: S110
                pass

    # ── Helpers ────────────────────────────────────────────────────

    def _infer_stage(self, event: Event) -> str:
        if event.type in {EventType.SCAN_STARTED, EventType.AGENT_STARTED}:
            return "enum"
        if event.type == EventType.CHECKPOINT_SAVED:
            return "validate"
        if event.type == EventType.FINDING_ADDED:
            return "report"
        if event.type in {EventType.TOOL_CALL_START, EventType.TOOL_CALL_COMPLETE}:
            tool = str(event.data.get("tool", ""))
            if any(k in tool for k in ("decompile", "manifest", "device_list", "search_decompiled")):
                return "enum"
            if any(k in tool for k in ("frida", "caido", "mobsf", "objection", "api")):
                return "attack"
            return "validate"
        return self._stage

    def _recovery_prompt(self) -> str:
        return {
            "enum": (
                "Flow recovery: run enumeration. Identify metadata, decompile artifact, "
                "analyze manifest/components/deep links, write attack surface."
            ),
            "attack": (
                "Flow recovery: convert leads into tests — deep links, exported components, "
                "API endpoints, WebView paths, auth/storage. Validate end-to-end."
            ),
            "validate": (
                "Flow recovery: evidence-driven validation. Reproduce with adb/frida, "
                "capture PoC steps, report severity/impact/remediation."
            ),
        }.get(
            self._stage,
            ("Flow recovery: continue scan — enumerate surfaces, validate top-risk hypotheses, checkpoint progress."),
        )
