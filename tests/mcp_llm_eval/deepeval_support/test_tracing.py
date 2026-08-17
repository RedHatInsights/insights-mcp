"""Unit tests for mcp_llm_eval.deepeval_support.tracing helpers."""

import pytest
from deepeval.test_case import ToolCall
from mcp_llm_eval.deepeval_support.tracing import (
    WorkflowToolCallCollector,
    tools_called_from_agent_output,
    tools_called_from_agent_run,
)


def test_workflow_tool_call_collector_records_all_calls():
    """Collector records every workflow tool invocation, including consecutive same-name calls."""
    collector = WorkflowToolCallCollector()
    collector.record("image-builder__get_blueprints", {"limit": 2})
    collector.record("image-builder__get_blueprints", {"limit": 3})
    collector.record("image-builder__get_composes", {})

    recorded = collector.as_list()
    assert recorded == [
        ToolCall(name="image-builder__get_blueprints", input_parameters={"limit": 2}),
        ToolCall(name="image-builder__get_blueprints", input_parameters={"limit": 3}),
        ToolCall(name="image-builder__get_composes", input_parameters={}),
    ]


def test_workflow_tool_call_collector_consume_event():
    """consume_event maps LlamaIndex workflow ToolCall events."""
    pytest.importorskip("llama_index.core.agent.workflow.workflow_events")
    from llama_index.core.agent.workflow.workflow_events import ToolCall as WorkflowToolCallEvent

    collector = WorkflowToolCallCollector()
    collector.consume_event(WorkflowToolCallEvent(tool_name="image-builder__get_openapi", tool_kwargs={}, tool_id="1"))

    assert collector.as_list() == [
        ToolCall(name="image-builder__get_openapi", input_parameters={}),
    ]


def test_tools_called_from_agent_output_maps_tool_selections():
    """AgentOutput.tool_calls are converted to DeepEval ToolCall records."""
    pytest.importorskip("llama_index.core.agent.workflow.workflow_events")
    from llama_index.core.agent.workflow.workflow_events import AgentOutput
    from llama_index.core.llms import ChatMessage
    from llama_index.core.tools import ToolSelection

    response = AgentOutput(
        response=ChatMessage(role="assistant", content="done"),
        current_agent_name="MCP Agent",
        tool_calls=[
            ToolSelection(tool_id="1", tool_name="image-builder__get_blueprints", tool_kwargs={"limit": 5}),
        ],
    )

    assert tools_called_from_agent_output(response) == [
        ToolCall(name="image-builder__get_blueprints", input_parameters={"limit": 5}),
    ]


def test_tools_called_from_agent_run_prefers_workflow_collector():
    """Workflow stream collector wins over empty AgentOutput.tool_calls."""
    pytest.importorskip("llama_index.core.agent.workflow.workflow_events")
    from llama_index.core.agent.workflow.workflow_events import AgentOutput
    from llama_index.core.llms import ChatMessage

    collector = WorkflowToolCallCollector()
    collector.record("image-builder__get_composes", {"limit": 1})
    response = AgentOutput(
        response=ChatMessage(role="assistant", content="ok"),
        current_agent_name="MCP Agent",
        tool_calls=[],
    )

    assert tools_called_from_agent_run(response, workflow_collector=collector) == [
        ToolCall(name="image-builder__get_composes", input_parameters={"limit": 1}),
    ]


def test_tools_called_from_agent_run_falls_back_to_agent_output():
    """When the collector is empty, AgentOutput.tool_calls are used."""
    pytest.importorskip("llama_index.core.agent.workflow.workflow_events")
    from llama_index.core.agent.workflow.workflow_events import AgentOutput
    from llama_index.core.llms import ChatMessage
    from llama_index.core.tools import ToolSelection

    response = AgentOutput(
        response=ChatMessage(role="assistant", content="ok"),
        current_agent_name="MCP Agent",
        tool_calls=[
            ToolSelection(tool_id="t1", tool_name="image-builder__get_openapi", tool_kwargs={}),
        ],
    )

    assert tools_called_from_agent_run(response, workflow_collector=WorkflowToolCallCollector()) == [
        ToolCall(name="image-builder__get_openapi", input_parameters={}),
    ]
