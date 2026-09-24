"""Test-only package for the reusable MCP LLM evaluation harness.

Import as ``tests.mcp_llm_eval``. It is not part of the installed application.
"""

from .data import PromptWithTools, TestScenario, TestScenarioRegistry

__all__ = [
    "PromptWithTools",
    "TestScenario",
    "TestScenarioRegistry",
]
