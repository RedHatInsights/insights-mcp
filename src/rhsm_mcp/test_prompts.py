"""Single source of truth for RHSM LLM test prompts."""

from mcp_llm_eval.data import PromptRegistry, TestScenario

TOOLSET_TITLE = "Red Hat Subscription Management (RHSM) MCP Test Prompts"

PROMPTS = PromptRegistry(
    list_activation_keys=TestScenario(
        turns=("Show me the list of activation keys",),
        expected_tools=("rhsm__get_activation_keys",),
    ),
)
