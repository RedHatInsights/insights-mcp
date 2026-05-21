"""Extract DeepEval ``ToolCall`` records from LlamaIndex agent runs."""

from typing import Any, List

from deepeval.test_case import ToolCall
from deepeval.tracing.tracing import trace_manager
from deepeval.tracing.types import BaseSpan, ToolSpan
from deepeval.tracing.utils import prepare_tool_call_input_parameters

try:
    from llama_index.core.agent.workflow.workflow_events import (
        AgentOutput,
    )
    from llama_index.core.agent.workflow.workflow_events import (
        ToolCall as WorkflowToolCallEvent,
    )
except ImportError:
    AgentOutput = None  # type: ignore[misc, assignment]
    WorkflowToolCallEvent = None  # type: ignore[misc, assignment]


def tool_call_from_workflow_event(event: Any) -> ToolCall | None:
    """Build a DeepEval ``ToolCall`` from a LlamaIndex workflow ``ToolCall`` event."""
    if WorkflowToolCallEvent is None or not isinstance(event, WorkflowToolCallEvent):
        return None
    return ToolCall(
        name=event.tool_name,
        input_parameters=dict(event.tool_kwargs or {}),
    )


class WorkflowToolCallCollector:
    """Accumulate tool invocations from workflow ``stream_events()``."""

    def __init__(self) -> None:
        self._calls: List[ToolCall] = []

    def record(self, tool_name: str, tool_kwargs: dict[str, Any] | None = None) -> None:
        """Append a tool call."""
        self._calls.append(ToolCall(name=tool_name, input_parameters=dict(tool_kwargs or {})))

    def consume_event(self, event: Any) -> None:
        """Record a tool call when ``event`` is a workflow ``ToolCall`` event."""
        tool_call = tool_call_from_workflow_event(event)
        if tool_call is not None:
            self.record(tool_call.name, tool_call.input_parameters)

    def as_list(self) -> List[ToolCall]:
        """Return collected tool calls."""
        return list(self._calls)

    def clear(self) -> None:
        """Reset collected tool calls (e.g. before an agent retry)."""
        self._calls.clear()


def tools_called_from_agent_output(response: Any) -> List[ToolCall]:
    """Map ``AgentOutput.tool_calls`` to DeepEval ``ToolCall`` instances."""
    if AgentOutput is None or not isinstance(response, AgentOutput):
        return []
    tool_calls: List[ToolCall] = []
    for selection in response.tool_calls or []:
        tool_calls.append(
            ToolCall(
                name=selection.tool_name,
                input_parameters=dict(selection.tool_kwargs or {}),
            )
        )
    return tool_calls


def _collect_tool_calls_from_span(span: BaseSpan) -> List[ToolCall]:
    collected: List[ToolCall] = []
    if span.tools_called:
        collected.extend(span.tools_called)
    if isinstance(span, ToolSpan):
        span_name = span.name
        if span_name and span_name != "Tool":
            collected.append(
                ToolCall(
                    name=span_name,
                    input_parameters=prepare_tool_call_input_parameters(span.input),
                )
            )
        elif isinstance(span.input, dict):
            tool_name = span.input.get("tool_name") or span.input.get("name")
            if tool_name:
                kwargs = span.input.get("tool_kwargs")
                if kwargs is None and "kwargs" in span.input:
                    kwargs = span.input["kwargs"]
                if not isinstance(kwargs, dict):
                    kwargs = prepare_tool_call_input_parameters(span.input)
                collected.append(ToolCall(name=str(tool_name), input_parameters=dict(kwargs or {})))
    for child in span.children:
        collected.extend(_collect_tool_calls_from_span(child))
    return collected


def tools_called_from_deepeval_traces() -> List[ToolCall]:
    """Aggregate tool calls from the most recent DeepEval trace (``instrument_llama_index``)."""
    traces = list(trace_manager.active_traces.values()) + list(trace_manager.traces)
    if not traces:
        return []
    trace = traces[-1]
    collected: List[ToolCall] = []
    if trace.tools_called:
        collected.extend(trace.tools_called)
    for root_span in trace.root_spans:
        collected.extend(_collect_tool_calls_from_span(root_span))
    return collected


def tools_called_from_agent_run(
    response: Any,
    workflow_collector: WorkflowToolCallCollector | None = None,
) -> List[ToolCall]:
    """Return tools invoked during an agent run.

    Prefer workflow stream events (multi-step), then DeepEval traces, then ``AgentOutput``.
    """
    if workflow_collector is not None:
        from_workflow = workflow_collector.as_list()
        if from_workflow:
            return from_workflow
    from_trace = tools_called_from_deepeval_traces()
    if from_trace:
        return from_trace
    return tools_called_from_agent_output(response)


__all__ = [
    "WorkflowToolCallCollector",
    "tool_call_from_workflow_event",
    "tools_called_from_agent_output",
    "tools_called_from_agent_run",
    "tools_called_from_deepeval_traces",
]
