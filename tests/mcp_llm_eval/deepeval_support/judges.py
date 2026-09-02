"""Reusable DeepEval evaluation helpers for MCP LLM tests."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence

from deepeval.metrics import BaseConversationalMetric, BaseMetric, ConversationalGEval, GEval, ToolCorrectnessMetric
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import (
    ConversationalTestCase,
    LLMTestCase,
    MultiTurnParams,
    SingleTurnParams,
    ToolCall,
    Turn,
)


def build_turn_test_case(
    prompt: str,
    response: str,
    tools_executed: Sequence[ToolCall],
    expected_tools: Sequence[str],
) -> LLMTestCase:
    """Build a DeepEval LLMTestCase from one agent execution turn."""
    return LLMTestCase(
        input=prompt,
        actual_output=response,
        tools_called=list(tools_executed),
        expected_tools=[ToolCall(name=name) for name in expected_tools],  # type: ignore[call-arg]
    )


def build_conversational_test_case(
    prompts: Sequence[str],
    responses: Sequence[str],
    tools_per_turn: Sequence[Sequence[ToolCall]],
) -> ConversationalTestCase:
    """Build a DeepEval conversation case from all executed scenario turns."""
    if not len(prompts) == len(responses) == len(tools_per_turn):
        raise ValueError("prompts, responses, and tools_per_turn must have the same length")

    turns: list[Turn] = []
    for prompt, response, tools_called in zip(prompts, responses, tools_per_turn):
        turns.extend(
            [
                Turn(role="user", content=prompt),
                Turn(role="assistant", content=response, tools_called=list(tools_called)),
            ]
        )

    return ConversationalTestCase(turns=turns)


async def _evaluate_metric(
    name: str,
    metric: BaseMetric | BaseConversationalMetric,
    measure: Callable[[], Awaitable[float]],
    logger: logging.Logger,
) -> None:
    """Measure a DeepEval metric, log its result, and fail below its threshold."""
    model_name = metric.model.name if metric.model else "guardian model"
    logger.info("🤔 Checking %s with %s…", name, model_name)
    await measure()
    if metric.score is None:
        raise RuntimeError(f"{name} did not produce a score")
    score = metric.score
    logger.info("📊 %s Score: %.2f (threshold: %.2f)", name, score, metric.threshold)
    logger.info("📝 %s Explanation: %s", name, metric.reason)
    assert metric.success, (
        f"{name} failed. Score: {score:.2f}, Threshold: {metric.threshold:.2f}. Reason: {metric.reason}"
    )


async def evaluate_tool_correctness(
    test_case: LLMTestCase,
    guardian_agent: DeepEvalBaseLLM,
    logger: logging.Logger,
    threshold: float = 0.6,
) -> None:
    """Evaluate tool selection correctness using DeepEval ToolCorrectnessMetric."""
    metric = ToolCorrectnessMetric(threshold=threshold, model=guardian_agent)
    await _evaluate_metric("Tool Correctness", metric, lambda: metric.a_measure(test_case), logger)


async def evaluate_compliance(
    test_case: LLMTestCase,
    criteria: str,
    guardian_agent: DeepEvalBaseLLM,
    logger: logging.Logger,
) -> None:
    """Evaluate one response against custom per-turn compliance criteria."""
    metric = GEval(
        name="Compliance Evaluation",
        criteria=criteria,
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.TOOLS_CALLED],
        model=guardian_agent,
    )
    await _evaluate_metric("Compliance Evaluation", metric, lambda: metric.a_measure(test_case), logger)


async def evaluate_behavioral(
    test_case: ConversationalTestCase,
    criteria: str,
    guardian_agent: DeepEvalBaseLLM,
    logger: logging.Logger,
) -> None:
    """Evaluate agent behavioral expectations across the complete conversation."""
    metric = ConversationalGEval(
        name="Behavioral Evaluation",
        criteria=criteria,
        evaluation_params=[MultiTurnParams.CONTENT, MultiTurnParams.ROLE, MultiTurnParams.TOOLS_CALLED],
        model=guardian_agent,
    )
    await _evaluate_metric("Behavioral Evaluation", metric, lambda: metric.a_measure(test_case), logger)
