"""Single source of truth for OCP Advisor LLM test prompts."""

from tests.mcp_llm_eval.data import PromptWithTools, TestScenario, TestScenarioRegistry

TOOLSET_TITLE = "OCP Advisor MCP Test Prompts"

PROMPTS = TestScenarioRegistry(
    deployed_rules_version=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Get the deployed ccx-ocp-rules version for OCP Advisor in production.",
                expected_tools=("ocp-advisor__get_info",),
            ),
        ),
    ),
    verify_rules_release=TestScenario(
        turns=(
            PromptWithTools(
                prompt=(
                    "Verify the latest OCP Advisor rules release was deployed to production "
                    "and show the Content Service commit and build metadata."
                ),
                expected_tools=("ocp-advisor__get_info",),
            ),
        ),
    ),
    production_stack_health=TestScenario(
        turns=(
            PromptWithTools(
                prompt=(
                    "Check that the OCP Advisor production backend is healthy across Smart Proxy, "
                    "Aggregator, and Content Service."
                ),
                expected_tools=("ocp-advisor__get_info",),
            ),
        ),
    ),
)
