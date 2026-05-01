from __future__ import annotations

import asyncio

import maya.tools  # noqa: F401
from maya.agents.state import AgentState, LeadState, LoopStage
from maya.decision.broker import DecisionRequest, get_decision_broker
from maya.tools.executor import execute_tool
from maya.tools.shared_context import get_shared_context_snapshot


def test_strict_sandbox_fails_closed_without_server() -> None:
    state = AgentState(
        agent_name="test",
        task="task",
        sandbox_mode="strict",
        decision_mode="auto_only",
        decision_timeout_seconds=1,
    )
    state.sandbox_info = {"server_url": "", "auth_token": "abc"}

    result = asyncio.run(execute_tool("terminal_execute", {"command": "echo hello"}, state))
    assert isinstance(result, dict)
    assert "error" in result
    assert "strict mode" in str(result["error"]).lower()


def test_decision_broker_auto_default_records_context() -> None:
    broker = get_decision_broker()
    broker.configure(decision_mode="auto_only", timeout_seconds=1)
    broker.set_ui_handler(None)

    state = AgentState(agent_name="test", task="task")
    response = asyncio.run(
        broker.request(
            DecisionRequest(
                prompt="High-risk action",
                options=["Proceed", "Gather More Evidence", "Skip"],
                safe_default="Gather More Evidence",
                timeout_seconds=1,
                context={"tool_name": "tamper_and_install"},
            ),
            agent_state=state,
        )
    )

    assert response.source == "auto"
    assert response.selected_option == "Gather More Evidence"
    assert state.decision_history
    shared = get_shared_context_snapshot()
    assert isinstance(shared.get("decision_history"), list)
    assert shared["decision_history"]


def test_loop_stage_and_budget_helpers() -> None:
    state = AgentState(agent_name="test", task="task", scan_time_budget_minutes=1)
    state.started_at = 0.0
    assert state.budget_exhausted()
    assert state.should_terminate()

    state = AgentState(agent_name="test", task="task")
    assert state.recompute_loop_stage() == LoopStage.ENUMERATE
    state.add_lead(title="Exported Activity", source="manifest")
    assert state.recompute_loop_stage() == LoopStage.VALIDATE
    state.mark_first_lead(LeadState.NEW, LeadState.VALIDATED)
    assert state.recompute_loop_stage() == LoopStage.EXPLOIT
    state.mark_first_lead(LeadState.VALIDATED, LeadState.EXPLOITED)
    assert state.recompute_loop_stage() == LoopStage.REPORT
