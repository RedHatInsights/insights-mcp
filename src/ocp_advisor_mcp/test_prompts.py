"""Single source of truth for OCP Advisor LLM test prompts."""

from tests.mcp_llm_eval.data import PromptWithTools, TestScenario, TestScenarioRegistry

TOOLSET_TITLE = "OCP Advisor MCP Test Prompts"

PROMPTS = TestScenarioRegistry(
    check_backend_status=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Check whether the OCP Advisor backend services are healthy.",
                expected_tools=("ocp-advisor__get_info",),
            ),
        ),
    ),
    show_service_metadata=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Show me the OCP Advisor service build and version metadata.",
                expected_tools=("ocp-advisor__get_info",),
            ),
        ),
    ),
    inspect_smart_proxy_status=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Is the OCP Advisor Smart Proxy reporting healthy status?",
                expected_tools=("ocp-advisor__get_info",),
            ),
        ),
    ),
    verify_aggregator_version=TestScenario(
        turns=(
            PromptWithTools(
                prompt="What Insights Results Aggregator version is the OCP Advisor backend running?",
                expected_tools=("ocp-advisor__get_info",),
            ),
        ),
    ),
    check_content_service_status=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Check the OCP Advisor Content Service status and build metadata.",
                expected_tools=("ocp-advisor__get_info",),
            ),
        ),
    ),
    release_verification=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Verify the deployed OCP Advisor backend commit hashes and service versions.",
                expected_tools=("ocp-advisor__get_info",),
            ),
        ),
    ),
)
