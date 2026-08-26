"""Single source of truth for RBAC LLM test prompts."""

from mcp_llm_eval.data import PromptRegistry, TestScenario

TOOLSET_TITLE = "RBAC MCP Test Prompts"

PROMPTS = PromptRegistry(
    my_insights_permissions=TestScenario(
        turns=("please check my insights permissions are there any missing for insights-mcp?",),
        expected_tools=("rbac__get_all_access",),
    ),
    user_access_across_apps=TestScenario(
        turns=('Show me access permissions for user "{rbac_username}" across all applications',),
        expected_tools=("rbac__get_all_access",),
    ),
    paginated_access=TestScenario(
        turns=("Get the first 50 access records across all applications",),
        expected_tools=("rbac__get_all_access",),
    ),
    service_account_access=TestScenario(
        turns=('What access permissions does service account "{rbac_username}" have across all Red Hat applications?',),
        expected_tools=("rbac__get_all_access",),
    ),
    debug_my_permissions=TestScenario(
        turns=(
            "I can't access certain features in Red Hat services. Show me all my access permissions "
            "across all applications to help debug the issue.",
        ),
        expected_tools=("rbac__get_all_access",),
    ),
    review_user_access=TestScenario(
        turns=(
            'Review access permissions for user "{rbac_username}" across all Red Hat applications '
            "to ensure they have appropriate access.",
        ),
        expected_tools=("rbac__get_all_access",),
    ),
)
