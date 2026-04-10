from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import click

from maya.agents.checkpointing import apply_checkpoint, load_latest_checkpoint
from maya.agents.maya_agent import MayaAgent
from maya.commands.apk_builder import build_apk as build_apk_command
from maya.llm import LLMClient, LLMConfig
from maya.models import ScanConfig
from maya.skills import list_available_skills_with_sources, set_cli_skills_dir
from maya.telemetry import Tracer
from maya.telemetry.event_bus import Event, EventBus, EventType

# ── Ensure unbuffered output for Docker / headless ──────────
os.environ.setdefault("PYTHONUNBUFFERED", "1")


def _detect_platform(package_path: str | None) -> str | None:
    """Infer platform from binary file extension."""
    if not package_path:
        return None
    ext = Path(package_path).suffix.lower()
    if ext == ".apk":
        return "android"
    if ext == ".ipa":
        return "ios"
    return None


def _build_task(target: str, platform: str | None, scan_mode: str) -> str:
    """Auto-generate a task description from target context."""
    plat = platform or "mobile"
    return (
        f"Perform a {scan_mode} mobile security assessment of {target} on {plat}. "
        f"Analyze the application statically, test dynamically on the connected device, "
        f"enumerate all attack surfaces (activities, services, content providers, broadcast "
        f"receivers, deep links, API endpoints), and report all security findings with "
        f"severity ratings, proof-of-concept steps, and remediation advice."
    )


def _is_headless() -> bool:
    """True when running without a TTY (e.g. Docker container)."""
    return not sys.stdout.isatty()


@click.command()
# ── Core args (the only ones you need) ──────────────────────
@click.option("-t", "--target", default=None, help="Target package name (e.g. com.app.example), or APK/IPA path")
@click.option("-p", "--package", default=None, type=click.Path(), help="Path to APK or IPA file")
@click.option("--device", default=None, help="Device serial (adb serial / iOS UDID)")
# ── Optional overrides ──────────────────────────────────────
@click.option("--platform", default=None, type=click.Choice(["android", "ios"]), help="Override auto-detected platform")
@click.option("--task", default=None, help="Override auto-generated task description")
@click.option(
    "-n", "--non-interactive", is_flag=True, default=False, help="Force headless mode (auto-detected in Docker)"
)
@click.option("--model", default=None, help="LiteLLM model string (default from env/config)")
@click.option("--api-key", default=None, help="LLM API key (default from env/config)")
# ── Advanced (hidden from --help) ───────────────────────────
@click.option(
    "--scan-mode", default="comprehensive", type=click.Choice(["quick", "standard", "comprehensive"]), hidden=True
)
@click.option("--instruction", default="", hidden=True)
@click.option("--instruction-file", default=None, hidden=True)
@click.option("--output-dir", default=None, hidden=True, help="Override auto output directory")
@click.option("--max-agents", default=7, type=int, hidden=True)
@click.option("--resume", default=None, hidden=True)
@click.option("--api-base", default=None, hidden=True)
@click.option("--skills-dir", default=None, hidden=True)
@click.option("--skills", default="", hidden=True)
@click.option("--default-skills", default="", hidden=True)
@click.option("--agent-skill", "agent_skills", multiple=True, hidden=True)
@click.option("--list-skills", "list_skills_flag", is_flag=True, default=False, hidden=True)
@click.option("--role", default="root", type=click.Choice(["root", "static", "dynamic", "api", "exploit"]), hidden=True)
# ── APK Build options (hidden, activated with --build-apk) ─────
@click.option(
    "--build-apk", is_flag=True, default=False, hidden=True, help="Build and sign companion APK"
)
@click.option("--apk-sign-mode", default="uber", type=click.Choice(["uber", "keystore"]), hidden=True)
@click.option("--apk-keystore", default=None, type=click.Path(exists=True), hidden=True)
@click.option("--apk-key-alias", default=None, hidden=True)
@click.option("--apk-store-pass", default=None, hidden=True)
@click.option("--apk-key-pass", default=None, hidden=True)
def cli(
    target: str | None,
    package: str | None,
    device: str | None,
    platform: str | None,
    task: str | None,
    non_interactive: bool,
    model: str | None,
    api_key: str | None,
    scan_mode: str,
    instruction: str,
    instruction_file: str | None,
    output_dir: str | None,
    max_agents: int,
    resume: str | None,
    api_base: str | None,
    skills_dir: str | None,
    skills: str,
    default_skills: str,
    agent_skills: tuple[str, ...],
    list_skills_flag: bool,
    role: str,
    build_apk: bool,
    apk_sign_mode: str,
    apk_keystore: str | None,
    apk_key_alias: str | None,
    apk_store_pass: str | None,
    apk_key_pass: str | None,
) -> None:
    """Maya \u2014 autonomous mobile security agent.

    \b
    Simple usage:
      maya --target com.app.example --package app.apk --device SERIAL
      maya --target com.app.example --device SERIAL
      maya --target com.app.example --package app.ipa
    """

    # ── Handle --build-apk (runs independently of scans) ──────
    if build_apk:
        exit_code = build_apk_command(
            sign_mode=apk_sign_mode,
            keystore_path=apk_keystore,
            key_alias=apk_key_alias,
            store_pass=apk_store_pass,
            key_pass=apk_key_pass,
        )
        raise SystemExit(exit_code)

    # ── Handle --list-skills before requiring --target ──────
    if list_skills_flag:
        set_cli_skills_dir(skills_dir)
        entries = list_available_skills_with_sources()
        if not entries:
            click.echo("No skills available")
            return
        click.echo("Available skills:")
        for entry in entries:
            description = f": {entry['description']}" if entry.get("description") else ""
            click.echo(f"- {entry['category']}/{entry['skill']}{description}")
        return

    # ── Compatibility shortcut: maya -t app.apk / app.ipa ──
    if target and not package:
        maybe_path = Path(target)
        if _detect_platform(target) and maybe_path.exists():
            package = target
            target = maybe_path.stem

    # ── If only --package is provided, derive target name ───
    if package and not target:
        target = Path(package).stem

    # ── Validate --target is provided for scans ─────────────
    if not target:
        raise click.UsageError("Missing option '--target'. Required for scanning. Tip: you can use 'maya -t app.apk'.")

    # ── Auto-detect platform from package extension ─────────
    if platform is None:
        platform = _detect_platform(package)

    # ── Auto-generate task if not provided ──────────────────
    if task is None:
        task = _build_task(target, platform, scan_mode)

    # ── Auto-set output directory ───────────────────────────
    if output_dir is None:
        output_dir = f"maya_runs/{target}"

    # ── Build targets list ──────────────────────────────────
    targets: list[dict[str, str]] = [{"type": "package", "value": target}]
    if package:
        targets.append({"type": "binary", "value": package})

    # ── Auto-detect headless (Docker / no TTY) ──────────────
    if not non_interactive and _is_headless():
        non_interactive = True

    async def _run() -> dict[str, Any]:
        set_cli_skills_dir(skills_dir)

        instruction_text = instruction
        if instruction_file:
            instruction_text = Path(instruction_file).read_text(encoding="utf-8")

        scan_config = ScanConfig(
            targets=targets,
            device_id=device,
            platform=platform,
            instruction=instruction_text,
            instruction_file=instruction_file,
            scan_mode=scan_mode,
            non_interactive=non_interactive,
            output_dir=output_dir,
            max_agents=max_agents,
            skills_dir=skills_dir,
            resume=resume,
        )

        config = LLMConfig.load().apply_overrides(
            model=model,
            api_key=api_key,
            api_base=api_base,
        )
        llm = LLMClient(config=config)
        
        # Validate LLM connection before starting scan
        await llm.validate()
        
        tracer = Tracer(run_dir=Path(scan_config.output_dir))
        tracer.log("scan_config", asdict(scan_config))

        run_name = Path(scan_config.output_dir).name

        parsed_skills = [s.strip() for s in skills.split(",") if s.strip()]
        parsed_default_skills = [s.strip() for s in default_skills.split(",") if s.strip()]
        merged_skills = list(
            dict.fromkeys(parsed_default_skills + parsed_skills + [s for s in agent_skills if s.strip()])
        )

        agent = MayaAgent(
            task=task,
            targets=targets,
            scan_mode=scan_mode,
            instruction=instruction_text,
            skills=merged_skills,
            llm=llm,
            device_id=device,
            platform=platform,
            role=role,
            run_name=run_name,
        )

        if resume:
            checkpoint = load_latest_checkpoint(run_name=resume)
            if checkpoint:
                apply_checkpoint(agent.state, checkpoint)
                tracer.log("resume", {"run": resume, "iteration": agent.state.iteration_count})

        return await agent.execute_scan()

    # ── Configure JSONL event logging ───────────────────────
    run_dir = Path(output_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    bus = EventBus.instance()
    bus.set_log_path(run_dir / "events.jsonl")

    if non_interactive:
        # ── Headless mode: print live progress to stderr ────
        async def _headless_subscriber(event: Event) -> None:
            t = event.type.value
            name = event.agent_name
            d = event.data
            if t == "agent_started":
                print(f"[+] Agent '{name}' started \u2014 {d.get('task', '')[:120]}", file=sys.stderr, flush=True)
            elif t == "agent_spawned":
                print(f"[+] Sub-agent '{name}' spawned", file=sys.stderr, flush=True)
            elif t == "iteration_start":
                print(f"  [{name}] iteration {d.get('iteration', '?')}", file=sys.stderr, flush=True)
            elif t == "llm_response":
                tokens = d.get("total_tokens", 0)
                cost = d.get("total_cost_usd", 0.0)
                cost_s = f"${cost:.4f}" if cost < 1 else f"${cost:.2f}"
                print(f"  [{name}] LLM response (cumulative: {tokens:,} tokens, {cost_s})", file=sys.stderr, flush=True)
            elif t == "tool_call_start":
                print(f"  [{name}] tool: {d.get('tool', '?')}", file=sys.stderr, flush=True)
            elif t == "tool_call_error":
                print(
                    f"  [{name}] TOOL ERROR: {d.get('tool', '?')} \u2014 {d.get('error', '')[:200]}",
                    file=sys.stderr,
                    flush=True,
                )
            elif t == "finding_added":
                sev = d.get("severity", "?").upper()
                print(f"  [{name}] FINDING [{sev}]: {d.get('title', '')}", file=sys.stderr, flush=True)
            elif t == "agent_completed":
                print(
                    f"[\u2713] Agent '{name}' completed \u2014 {d.get('findings', 0)} findings",
                    file=sys.stderr,
                    flush=True,
                )
            elif t == "agent_failed":
                print(f"[\u2717] Agent '{name}' FAILED: {d.get('error', '')[:200]}", file=sys.stderr, flush=True)

        bus.subscribe(_headless_subscriber)

        print(f"\n{'=' * 60}", file=sys.stderr, flush=True)
        print("  Maya \u2014 Autonomous Mobile Security Agent", file=sys.stderr, flush=True)
        print(f"  Target:   {target}", file=sys.stderr, flush=True)
        if package:
            print(f"  Package:  {package}", file=sys.stderr, flush=True)
        if device:
            print(f"  Device:   {device}", file=sys.stderr, flush=True)
        print(f"  Platform: {platform or 'auto'}", file=sys.stderr, flush=True)
        print(f"  Mode:     {scan_mode}", file=sys.stderr, flush=True)
        print(f"  Output:   {output_dir}", file=sys.stderr, flush=True)
        print(f"{'=' * 60}\n", file=sys.stderr, flush=True)

        try:
            result = asyncio.run(_run())
        except Exception as exc:
            import traceback

            print(f"\n[FATAL] Scan crashed: {exc}", file=sys.stderr, flush=True)
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            raise SystemExit(1) from exc

        tracer = Tracer(run_dir=run_dir)
        for f in result.get("findings", []):
            tracer.record_finding(f)
        for ep in result.get("api_endpoints", []):
            tracer.record_api_endpoint(ep)
        tracer.log("scan_result", {"status": result.get("status"), "iterations": result.get("iterations")})
        tracer.persist()

        print(f"\n{'=' * 60}", file=sys.stderr, flush=True)
        print("  Maya scan complete", file=sys.stderr, flush=True)
        print(f"  Status:     {result['status']}", file=sys.stderr, flush=True)
        print(f"  Iterations: {result['iterations']}", file=sys.stderr, flush=True)
        print(f"  Tool calls: {result['tool_calls']}", file=sys.stderr, flush=True)
        print(f"  Findings:   {len(result['findings'])}", file=sys.stderr, flush=True)
        print(f"  Output:     {output_dir}", file=sys.stderr, flush=True)
        print(f"{'=' * 60}", file=sys.stderr, flush=True)
    else:
        # ── Interactive: launch Textual TUI ─────────────────
        from maya.ui.app import MayaUI

        _scan_ui_config = {
            "target": targets[0].get("value", "—") if targets else "—",
            "package": package or "—",
            "device": device or "—",
            "platform": platform or "auto",
            "model": model or os.environ.get("MAYA_LLM", "—"),
            "scan_mode": scan_mode or "comprehensive",
        }

        _agent_ref: dict[str, Any] = {}

        async def _on_user_input(message: str, agent_id: str | None) -> None:
            agent = _agent_ref.get("agent")
            if agent and hasattr(agent, "state"):
                agent.state.add_message("user", message)

        async def _scan_worker() -> None:
            await bus.emit(
                Event(
                    type=EventType.SCAN_STARTED,
                    agent_id="root",
                    agent_name="root",
                    data={"task": task, "targets": targets},
                )
            )
            result = await _build_and_run_agent()
            await bus.emit(
                Event(
                    type=EventType.SCAN_COMPLETED,
                    agent_id="root",
                    agent_name="root",
                    data=result,
                )
            )
            tracer = Tracer(run_dir=run_dir)
            for f in result.get("findings", []):
                tracer.record_finding(f)
            for ep in result.get("api_endpoints", []):
                tracer.record_api_endpoint(ep)
            tracer.log("scan_result", {"status": result.get("status"), "iterations": result.get("iterations")})
            tracer.persist()

        async def _build_and_run_agent() -> dict[str, Any]:
            set_cli_skills_dir(skills_dir)
            instruction_text = instruction
            if instruction_file:
                instruction_text = Path(instruction_file).read_text(encoding="utf-8")

            scan_config = ScanConfig(
                targets=targets,
                device_id=device,
                platform=platform,
                instruction=instruction_text,
                instruction_file=instruction_file,
                scan_mode=scan_mode,
                non_interactive=False,
                output_dir=output_dir,
                max_agents=max_agents,
                skills_dir=skills_dir,
                resume=resume,
            )

            config = LLMConfig.load().apply_overrides(
                model=model,
                api_key=api_key,
                api_base=api_base,
            )
            llm = LLMClient(config=config)
            
            # Validate LLM connection before starting scan
            await llm.validate()

            run_name = Path(scan_config.output_dir).name
            parsed_skills = [s.strip() for s in skills.split(",") if s.strip()]
            parsed_default_skills = [s.strip() for s in default_skills.split(",") if s.strip()]
            merged_skills = list(
                dict.fromkeys(parsed_default_skills + parsed_skills + [s for s in agent_skills if s.strip()])
            )

            agent = MayaAgent(
                task=task,
                targets=targets,
                scan_mode=scan_mode,
                instruction=instruction_text,
                skills=merged_skills,
                llm=llm,
                device_id=device,
                platform=platform,
                role=role,
                run_name=run_name,
            )
            _agent_ref["agent"] = agent

            if resume:
                checkpoint = load_latest_checkpoint(run_name=resume)
                if checkpoint:
                    apply_checkpoint(agent.state, checkpoint)

            return await agent.execute_scan()

        app = MayaUI(
            run_dir=run_dir,
            scan_config=_scan_ui_config,
            scan_worker=_scan_worker,
            on_user_input=_on_user_input,
        )
        app.run()


if __name__ == "__main__":
    cli()
