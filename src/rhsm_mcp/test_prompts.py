"""Single source of truth for RHSM LLM test prompts."""

from insights_mcp.test_prompts_data import PromptRegistry, PromptWithTools

TOOLSET_TITLE = "Red Hat Subscription Management (RHSM) MCP Test Prompts"

PROMPTS = PromptRegistry(
    list_activation_keys=PromptWithTools(
        turns=("Show me the list of activation keys",),
        expected_tools=("rhsm__get_activation_keys",),
    ),
)
