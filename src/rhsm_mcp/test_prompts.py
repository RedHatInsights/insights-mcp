"""Single source of truth for RHSM LLM test prompts."""

from mcp_llm_eval.data import PromptWithTools, TestScenario, TestScenarioRegistry

TOOLSET_TITLE = "Red Hat Subscription Management (RHSM) MCP Test Prompts"

PROMPTS = TestScenarioRegistry(
    list_activation_keys=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Show me the list of activation keys",
                expected_tools=("rhsm__get_activation_keys",),
            ),
        ),
    ),
)
