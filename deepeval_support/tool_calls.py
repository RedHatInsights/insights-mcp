"""Construct DeepEval ToolCall instances for recordings from MCP agents."""

from typing import Any

from deepeval.test_case import ToolCall


def tool_call_record(tool_name: str, input_parameters: dict[str, Any]) -> ToolCall:
    """Return a Deepeval ``ToolCall`` for a wrapped MCP tool invocation."""
    return ToolCall(name=tool_name, input_parameters=input_parameters)


__all__ = ["tool_call_record"]
