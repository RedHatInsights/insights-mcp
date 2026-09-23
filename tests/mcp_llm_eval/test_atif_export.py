"""Unit tests for ATIF export helpers (no live Phoenix)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tests.mcp_llm_eval import atif_export


def test_node_display_id_strips_module_path():
    """Filename stem is Class::test[params], copy-pasteable without the module path."""
    node_id = (
        "src/advisor_mcp/tests/test_advisor_llm_prompts.py::"
        "TestAdvisorLLMPrompts::test_llm_eval[top_critical_issues-Gemini 2.5 Flash]"
    )
    assert atif_export.node_display_id(node_id) == (
        "TestAdvisorLLMPrompts::test_llm_eval[top_critical_issues-Gemini 2.5 Flash]"
    )


def test_node_display_id_without_py_marker():
    """Node ids without a .py:: marker keep the last path component."""
    assert atif_export.node_display_id("tests/foo.py") == "foo.py"
    assert atif_export.node_display_id("TestClass::test_one") == "TestClass::test_one"


def test_trace_export_disabled_reads_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """INSIGHTS_MCP_DISABLE_TRACE_EXPORT accepts conventional truthy values."""
    monkeypatch.delenv(atif_export.DISABLE_TRACE_EXPORT_ENV, raising=False)
    assert atif_export.trace_export_disabled() is False
    monkeypatch.setenv(atif_export.DISABLE_TRACE_EXPORT_ENV, "true")
    assert atif_export.trace_export_disabled() is True
    monkeypatch.setenv(atif_export.DISABLE_TRACE_EXPORT_ENV, "0")
    assert atif_export.trace_export_disabled() is False


def test_ensure_phoenix_ready_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Disable env skips the live-upload client check even if the endpoint is set."""
    monkeypatch.setenv(atif_export.DISABLE_TRACE_EXPORT_ENV, "1")
    monkeypatch.setenv(atif_export.PHOENIX_COLLECTOR_ENDPOINT_ENV, "http://localhost:6006")
    monkeypatch.setattr(atif_export, "Client", None)
    monkeypatch.setattr(atif_export, "_convert_atif_trajectories_to_spans", None)
    atif_export.ensure_phoenix_ready()


def test_ensure_phoenix_ready_ok_without_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """File export does not require the Phoenix package."""
    monkeypatch.delenv(atif_export.DISABLE_TRACE_EXPORT_ENV, raising=False)
    monkeypatch.delenv(atif_export.PHOENIX_COLLECTOR_ENDPOINT_ENV, raising=False)
    monkeypatch.setattr(atif_export, "Client", None)
    monkeypatch.setattr(atif_export, "_convert_atif_trajectories_to_spans", None)
    atif_export.ensure_phoenix_ready()


def test_require_phoenix_client_asks_for_pip_install(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing client tells the user to pip install or unset the endpoint."""
    monkeypatch.setattr(atif_export, "Client", None)
    monkeypatch.setattr(atif_export, "_convert_atif_trajectories_to_spans", None)
    with pytest.raises(RuntimeError, match="uv pip install arize-phoenix-client"):
        atif_export.require_phoenix_client()


def test_ensure_phoenix_ready_errors_when_endpoint_set_without_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live upload requested without the package is a hard error."""
    monkeypatch.delenv(atif_export.DISABLE_TRACE_EXPORT_ENV, raising=False)
    monkeypatch.setenv(atif_export.PHOENIX_COLLECTOR_ENDPOINT_ENV, "http://localhost:6006")
    monkeypatch.setattr(atif_export, "Client", None)
    monkeypatch.setattr(atif_export, "_convert_atif_trajectories_to_spans", None)
    with pytest.raises(RuntimeError, match="Unset PHOENIX_COLLECTOR_ENDPOINT"):
        atif_export.ensure_phoenix_ready()


def test_apply_pytest_span_status_marks_only_failed_agent_root() -> None:
    """Failed AGENT roots become ERROR; passed roots and child spans stay OK."""
    spans: list[dict[str, Any]] = [
        {"name": "passed-test", "parent_id": None, "span_kind": "AGENT", "status_code": "OK"},
        {
            "name": "failed-test",
            "parent_id": None,
            "span_kind": "AGENT",
            "status_code": "OK",
        },
        {"name": "iteration 1", "parent_id": "abc", "span_kind": "CHAIN", "status_code": "OK"},
    ]
    trajectories: list[dict[str, Any]] = [
        {"agent": {"name": "passed-test"}, "extra": {"pytest_outcome": "passed"}},
        {
            "agent": {"name": "failed-test"},
            "extra": {
                "pytest_outcome": "failed",
                "pytest_status_message": "Tool Correctness Score: 0.50",
            },
        },
    ]
    atif_export.apply_pytest_span_status(spans, trajectories)
    assert spans[0]["status_code"] == "OK"
    assert "status_message" not in spans[0]
    assert spans[1]["status_code"] == "ERROR"
    assert spans[1]["status_message"] == "Tool Correctness Score: 0.50"
    assert spans[2]["status_code"] == "OK"


class ToolCall:  # pylint: disable=too-few-public-methods
    """Test double whose class name matches LlamaIndex workflow ToolCall."""

    def __init__(self, tool_name: str, tool_kwargs: dict[str, object], tool_id: str) -> None:
        self.tool_name = tool_name
        self.tool_kwargs = tool_kwargs
        self.tool_id = tool_id


class ToolCallResult:  # pylint: disable=too-few-public-methods
    """Test double whose class name matches LlamaIndex workflow ToolCallResult."""

    def __init__(self, tool_id: str, content: str) -> None:
        self.tool_id = tool_id
        self.tool_output = SimpleNamespace(content=content, blocks=[])


class AgentOutput:  # pylint: disable=too-few-public-methods
    """Test double whose class name matches LlamaIndex workflow AgentOutput."""

    def __init__(self, content: str) -> None:
        self.response = SimpleNamespace(content=content, blocks=[])


def _builder() -> atif_export.AtifTrajectoryBuilder:
    return atif_export.AtifTrajectoryBuilder(
        session_id="20260922125600",
        trajectory_id="TestAdvisorLLMPrompts::test_llm_eval[top_critical_issues-Gemini 2.5 Flash]",
        pytest_node_id=(
            "src/advisor_mcp/tests/test_advisor_llm_prompts.py::"
            "TestAdvisorLLMPrompts::test_llm_eval[top_critical_issues-Gemini 2.5 Flash]"
        ),
        model_name="gemini-2.5-flash",
        tool_definitions=[
            {
                "type": "function",
                "function": {
                    "name": "advisor__get_active_rules",
                    "description": "Get active Advisor Recommendations for the account.",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
        test_file="tests/mcp_llm_eval/generators.py",
        test_line=43,
    )


def test_atif_builder_records_user_tool_and_assistant_steps() -> None:
    """Synthetic workflow events become an ATIF trajectory with pytest metadata."""
    builder = _builder()
    builder.begin_turn("Show me the top 5 critical issues on my systems")
    builder.consume_event(AgentOutput(""))
    builder.consume_event(ToolCall("advisor__get_active_rules", {"impacting": True, "limit": 5}, "call-1"))
    builder.consume_event(ToolCallResult("call-1", '{"meta": {"count": 0}, "data": []}'))
    builder.consume_event(AgentOutput("I couldn't find any critical issues impacting your systems."))
    trajectory = builder.finish(pytest_outcome="passed")

    assert trajectory["schema_version"] == "ATIF-v1.7"
    assert trajectory["agent"]["name"] == trajectory["trajectory_id"]
    assert trajectory["extra"]["pytest_outcome"] == "passed"
    assert trajectory["extra"]["test_file"] == "tests/mcp_llm_eval/generators.py"
    assert trajectory["extra"]["test_line"] == 43
    sources = [step["source"] for step in trajectory["steps"]]
    assert sources == ["user", "agent"]
    agent_step = trajectory["steps"][1]
    assert agent_step["tool_calls"][0]["function_name"] == "advisor__get_active_rules"
    assert agent_step["tool_calls"][0]["arguments"] == {"impacting": True, "limit": 5}
    assert agent_step["observation"]["results"][0]["content"] == '{"meta": {"count": 0}, "data": []}'
    assert agent_step["message"] == "I couldn't find any critical issues impacting your systems."
    assert trajectory["final_metrics"]["total_steps"] == 2


def test_atif_builder_failed_outcome_and_status_message() -> None:
    """Failed pytest outcome is copied onto trajectory extra and every step."""
    builder = _builder()
    builder.begin_turn("prompt")
    builder.consume_event(AgentOutput("done"))
    trajectory = builder.finish(
        pytest_outcome="failed",
        pytest_status_message="Tool Correctness Score: 0.50 (threshold: 0.60)",
    )
    assert trajectory["extra"]["pytest_outcome"] == "failed"
    assert "0.50" in trajectory["extra"]["pytest_status_message"]
    assert trajectory["agent"]["extra"]["pytest_outcome"] == "failed"
    assert trajectory["steps"][0]["extra"]["pytest_outcome"] == "failed"
    assert trajectory["steps"][1]["extra"]["pytest_outcome"] == "failed"


def test_atif_builder_reset_turn_drops_retry_attempt() -> None:
    """Empty-response retry replaces the failed turn instead of duplicating it."""
    builder = _builder()
    builder.begin_turn("prompt")
    builder.consume_event(ToolCall("advisor__get_active_rules", {}, "call-1"))
    builder.consume_event(ToolCallResult("call-1", "{}"))
    builder.reset_turn("prompt")
    builder.consume_event(AgentOutput("ok"))
    trajectory = builder.finish(pytest_outcome="passed")
    assert [step["source"] for step in trajectory["steps"]] == ["user", "agent"]
    assert "tool_calls" not in trajectory["steps"][1]
    assert trajectory["steps"][1]["message"] == "ok"


def test_atif_builder_one_step_per_completed_tool_round() -> None:
    """A new ToolCall after a completed observation starts a separate agent step."""
    builder = _builder()
    builder.begin_turn("kb article")
    builder.consume_event(ToolCall("advisor__get_rule_from_node_id", {"node_id": 1}, "c1"))
    builder.consume_event(ToolCallResult("c1", '["rule-a"]'))
    builder.consume_event(ToolCall("advisor__get_hosts_hitting_a_rule", {"rule_id": "rule-a"}, "c2"))
    builder.consume_event(ToolCallResult("c2", '{"host_ids": []}'))
    builder.consume_event(AgentOutput("none of your systems are affected"))
    trajectory = builder.finish(pytest_outcome="passed")
    agent_steps = [step for step in trajectory["steps"] if step["source"] == "agent"]
    assert len(agent_steps) == 2
    assert agent_steps[0]["tool_calls"][0]["function_name"] == "advisor__get_rule_from_node_id"
    assert agent_steps[1]["tool_calls"][0]["function_name"] == "advisor__get_hosts_hitting_a_rule"
    assert agent_steps[1]["message"] == "none of your systems are affected"


def test_tool_definitions_from_tools_uses_metadata() -> None:
    """FunctionTool-like objects map to ATIF function definitions."""
    schema = SimpleNamespace(
        model_json_schema=lambda: {
            "type": "object",
            "properties": {"limit": {"type": "integer"}},
            "required": ["limit"],
        }
    )
    tool = SimpleNamespace(
        metadata=SimpleNamespace(
            name="advisor__get_active_rules",
            description="Get active rules",
            fn_schema=schema,
        )
    )
    definitions = atif_export.tool_definitions_from_tools([tool])
    assert definitions == [
        {
            "type": "function",
            "function": {
                "name": "advisor__get_active_rules",
                "description": "Get active rules",
                "parameters": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer"}},
                    "required": ["limit"],
                },
            },
        }
    ]


def test_write_atif_json_round_trip(tmp_path: Path) -> None:
    """Serialized trajectories load back as the same object."""
    builder = _builder()
    builder.begin_turn("hello")
    builder.consume_event(AgentOutput("world"))
    trajectory = builder.finish(pytest_outcome="passed")
    path = tmp_path / "out.json"
    atif_export.write_atif_json(path, trajectory)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == trajectory
    assert loaded["agent"]["name"] == loaded["trajectory_id"]
