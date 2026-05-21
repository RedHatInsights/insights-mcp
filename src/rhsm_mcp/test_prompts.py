"""Single source of truth for RHSM LLM test prompts."""

from insights_mcp.test_prompts_data import PromptRegistry

TOOLSET_TITLE = "Red Hat Subscription Management (RHSM) MCP Test Prompts"

PROMPTS = PromptRegistry(
    list_activation_keys=(
        "Show me the list of activation keys",
        ("rhsm__get_activation_keys",),
    ),
)
