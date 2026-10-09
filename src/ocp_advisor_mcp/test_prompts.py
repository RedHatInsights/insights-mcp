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
                prompt="Verify the released OCP Advisor rules were deployed successfully to production.",
                expected_tools=("ocp-advisor__get_info",),
            ),
        ),
    ),
    content_service_release_details=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Show the OCP Advisor Content Service build commit and OCP rules version.",
                expected_tools=("ocp-advisor__get_info",),
            ),
        ),
    ),
    confirm_content_service_health=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Confirm the OCP Advisor Content Service is healthy after the rules release.",
                expected_tools=("ocp-advisor__get_info",),
            ),
        ),
    ),
    aggregator_database_versions=TestScenario(
        turns=(
            PromptWithTools(
                prompt="What OCP_DB_version and DVO_DB_version is the OCP Advisor Aggregator using?",
                expected_tools=("ocp-advisor__get_info",),
            ),
        ),
    ),
    backend_deployment_metadata=TestScenario(
        turns=(
            PromptWithTools(
                prompt="List the deployed OCP Advisor backend build times, commits, versions, and statuses.",
                expected_tools=("ocp-advisor__get_info",),
            ),
        ),
    ),
    smart_proxy_health=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Is the OCP Advisor Smart Proxy healthy, and which utility version is it running?",
                expected_tools=("ocp-advisor__get_info",),
            ),
        ),
    ),
    production_stack_health=TestScenario(
        turns=(
            PromptWithTools(
                prompt=(
                    "Check that Smart Proxy, Aggregator, and Content Service are all healthy in OCP Advisor production."
                ),
                expected_tools=("ocp-advisor__get_info",),
            ),
        ),
    ),
)
