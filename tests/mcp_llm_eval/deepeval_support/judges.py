"""Reusable deepeval evaluation helpers for MCP LLM tests."""

from __future__ import annotations

import logging
from typing import Any

from deepeval.metrics import GEval, ToolCorrectnessMetric
from deepeval.test_case import LLMTestCase, SingleTurnParams, ToolCall


def build_test_case(
    prompt: str,
    response: str,
    tools_executed: list[Any],
    expected_tools: list[str],
) -> LLMTestCase:
    """Build a deepeval LLMTestCase from agent execution results."""
    return LLMTestCase(
        input=prompt,
        actual_output=response,
        tools_called=tools_executed,
        expected_tools=[ToolCall(name=name) for name in expected_tools],  # type: ignore[call-arg]
    )


async def _evaluate_geval(
    name: str,
    test_case: LLMTestCase,
    criteria: str,
    evaluation_params: list[SingleTurnParams],
    guardian_agent: Any,
    logger: logging.Logger,
) -> None:
    metric = GEval(
        name=name,
        criteria=criteria,
        evaluation_params=evaluation_params,
        model=guardian_agent,
    )
    logger.info("🤔 Checking response with %s…", guardian_agent.name)
    await metric.a_measure(test_case)
    logger.info("📊 %s Score: %.2f (threshold: %.2f)", name, metric.score, metric.threshold)
    logger.info("📝 %s Explanation: %s", name, metric.reason)
    assert metric.success, (
        f"{name} failed. Score: {metric.score:.2f}, Threshold: {metric.threshold:.2f}. Reason: {metric.reason}"
    )


async def evaluate_tool_correctness(
    test_case: LLMTestCase,
    guardian_agent: Any,
    logger: logging.Logger,
    threshold: float = 0.6,
) -> None:
    """Evaluate tool selection correctness using deepeval ToolCorrectnessMetric."""
    metric = ToolCorrectnessMetric(threshold=threshold, model=guardian_agent)
    await metric.a_measure(test_case)
    logger.info("📊 Tool Correctness Score: %.2f (threshold: %.2f)", metric.score, metric.threshold)
    logger.info("📝 Tool Correctness Explanation: %s", metric.reason)
    assert metric.success, (
        f"Tool correctness failed. Score: {metric.score:.2f}, "
        f"Threshold: {metric.threshold:.2f}. Reason: {metric.reason}"
    )


async def evaluate_compliance(
    test_case: LLMTestCase,
    criteria: str,
    guardian_agent: Any,
    logger: logging.Logger,
) -> None:
    """Evaluate response compliance against custom criteria using GEval."""
    await _evaluate_geval(
        "Compliance Evaluation",
        test_case,
        criteria,
        [SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.TOOLS_CALLED],
        guardian_agent,
        logger,
    )


async def evaluate_behavioral(
    test_case: LLMTestCase,
    criteria: str,
    guardian_agent: Any,
    logger: logging.Logger,
) -> None:
    """Evaluate agent behavioral expectations using GEval."""
    await _evaluate_geval(
        "Behavioral Evaluation",
        test_case,
        criteria,
        [SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.TOOLS_CALLED],
        guardian_agent,
        logger,
    )
