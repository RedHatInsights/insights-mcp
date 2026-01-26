"""Base class for LLM integration tests using rubric-kit.

This module provides a reusable base class for testing LLM behavior with MCP servers
using rubric-kit's judge panel approach. Subclasses only need to define a few
class attributes to create a new test.

Example usage:
    # test_llm_my_feature.py
    from .test_llm_base import BaseLLMRubricTest

    class TestLLMMyFeature(BaseLLMRubricTest):
        TEST_PROMPT = "Your test prompt here"
        REPORT_TITLE = "My Feature Test"
        EXPECTED_TOOL = "my_toolset__my_tool"  # Optional: tool that must be called

Example factory function:
    TestMyFeature = create_llm_test_class(
        test_prompt="Your test prompt here",
        report_title="My Feature Test",
        expected_tool="my_toolset__my_tool",
        rubric_path="path/to/rubric.yaml"
    )
"""

import os
from abc import ABC
from pathlib import Path

import pytest
from rubric_kit.validator import load_judge_panel_config

from tests.utils import should_skip_llm_matrix_tests
from tests.utils_rubric import (
    check_passing_threshold,
    check_tool_correctness,
    check_tool_input_parameters,
    evaluate_with_rubric,
    format_chat_session,
    generate_report,
    prompt_test_agent,
)

from .constants import LLM_CONFIGURATIONS, PANEL_PATH, PASSING_THRESHOLD, TEST_DIR
from .utils.yaml_include import load_rubric_with_includes


class BaseRubricTest(ABC):
    """Base class for Rubric integration tests using rubric-kit.

    Subclasses must define:
        TEST_PROMPT: str - The user prompt to test
        REPORT_TITLE: str - Title for the generated report

    Subclasses may optionally define:
        RUBRIC_PATH: Path - Path to the rubric YAML file (defaults to auto-derived)
        EXPECTED_TOOL: str | None - Tool that must be called (for tool_correctness assertion)
        PASSING_THRESHOLD: float - Minimum passing percentage (defaults to global constant)
    """

    # Required attributes (must be overridden by subclasses)
    TEST_PROMPT: str = NotImplemented
    REPORT_TITLE: str = NotImplemented

    # Optional attributes
    RUBRIC_PATH: Path | None = None  # Auto-derived from module name if None
    EXPECTED_TOOL: str | None = None  # Tool that must be called (checked in assertion message)
    EXPECTED_TOOL_INPUT_PARAMETERS: dict | None = None  # Tool input parameters that must be passed down
    PASSING_THRESHOLD: float = PASSING_THRESHOLD  # Can override the default

    @classmethod
    def get_rubric_path(cls) -> Path:
        """Get the rubric path, auto-deriving from module name if not explicitly set."""
        if cls.RUBRIC_PATH is not None:
            return cls.RUBRIC_PATH
        # Derive from module name: test_llm_foo -> test_llm_foo_rubric.yaml
        module_name = cls.__module__.rsplit(".", 1)[-1]
        return TEST_DIR / f"{module_name}_rubric.yaml"

    @pytest.mark.asyncio
    async def test_llm_behavior(self, test_agent, verbose_logger, llm_config):
        """Test LLM behavior with MCP server using rubric-kit evaluation.

        This method:
        1. Executes the test prompt with the LLM agent
        2. Formats the response for rubric-kit evaluation
        3. Evaluates against the rubric using judge panel
        4. Generates PDF/YAML reports
        5. Asserts minimum passing threshold and tool usage
        """
        verbose_logger.info("Testing model: %s", llm_config["name"])
        verbose_logger.info(
            "Test prompt: %s", self.TEST_PROMPT[:100] + "..." if len(self.TEST_PROMPT) > 100 else self.TEST_PROMPT
        )

        # Load rubric and judge panel configuration
        rubric_path = self.get_rubric_path()
        verbose_logger.info("Using rubric: %s", rubric_path)
        rubric = load_rubric_with_includes(str(rubric_path))
        panel_config = load_judge_panel_config(str(PANEL_PATH))

        # Execute the test prompt
        response, tools_executed = await prompt_test_agent(test_agent, self.TEST_PROMPT, verbose_logger)

        # Format the chat session for rubric-kit
        chat_content = format_chat_session(self.TEST_PROMPT, response, tools_executed)

        # Evaluate the response with the rubric and judge panel
        results, total_score, max_score, percentage = await evaluate_with_rubric(
            rubric, chat_content, panel_config, verbose_logger
        )

        test_result = "Pass"
        try:
            # Verify the critical tool was called (if specified)
            check_tool_correctness(results, self.EXPECTED_TOOL)

            # Verify tool parameters
            check_tool_input_parameters(tools_executed, self.EXPECTED_TOOL_INPUT_PARAMETERS)

            # Assert minimum passing threshold
            check_passing_threshold(results, percentage, self.PASSING_THRESHOLD)
        except Exception:
            test_result = "Fail"
            raise
        finally:
            # Generate reports
            if os.getenv("GENERATE_REPORTS", "false").lower() == "true":
                generate_report(
                    results,
                    rubric,
                    panel_config,
                    llm_config,
                    total_score,
                    max_score,
                    percentage,
                    chat_content,
                    verbose_logger,
                    reports_dir=TEST_DIR / "reports",
                    report_title=f"{test_result} - {self.REPORT_TITLE} ({llm_config.get('name', 'Unknown Model')})",
                    test_prompt=self.TEST_PROMPT,
                )


def create_rubric_test_class(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    test_prompt: str,
    report_title: str,
    rubric_path: Path | None = None,
    expected_tool: str | None = None,
    expected_tool_input_parameters: dict | None = None,
    passing_threshold: float = PASSING_THRESHOLD,
):
    """Factory function to create a configured LLM test class.

    This is an alternative to class inherit for simple cases.

    Example:
        TestMyFeature = create_llm_test_class(
            test_prompt="What are the upcoming changes?",
            report_title="My Feature Test",
            expected_tool="planning__get_upcoming_changes"
        )
    """

    @pytest.mark.skipif(should_skip_llm_matrix_tests(), reason="No LLM configurations available")
    @pytest.mark.parametrize("llm_config", LLM_CONFIGURATIONS, ids=lambda c: c.get("name", "Unknown Model"))
    class ConfiguredRubricTest(BaseRubricTest):
        """Dynamically configured rubric test class created by the factory function."""

        TEST_PROMPT = test_prompt
        REPORT_TITLE = report_title
        RUBRIC_PATH = rubric_path
        EXPECTED_TOOL = expected_tool
        EXPECTED_TOOL_INPUT_PARAMETERS = expected_tool_input_parameters
        PASSING_THRESHOLD = passing_threshold

    return ConfiguredRubricTest
