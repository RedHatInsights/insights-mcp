"""Single source of truth for RBAC LLM test prompts."""

from insights_mcp.test_prompts_data import PromptRegistry, PromptWithTools

TOOLSET_TITLE = "RBAC MCP Test Prompts"

PROMPTS = PromptRegistry(
    my_insights_permissions=PromptWithTools(
        turns=("please check my insights permissions are there any missing for insights-mcp?",),
        expected_tools=("rbac__get_all_access",),
    ),
    user_access_across_apps=PromptWithTools(
        turns=('Show me access permissions for user "{rbac_username}" across all applications',),
        expected_tools=("rbac__get_all_access",),
    ),
    paginated_access=PromptWithTools(
        turns=("Get the first 50 access records across all applications",),
        expected_tools=("rbac__get_all_access",),
    ),
    service_account_access=PromptWithTools(
        turns=('What access permissions does service account "{rbac_username}" have across all Red Hat applications?',),
        expected_tools=("rbac__get_all_access",),
    ),
    debug_my_permissions=PromptWithTools(
        turns=(
            "I can't access certain features in Red Hat services. Show me all my access permissions "
            "across all applications to help debug the issue.",
        ),
        expected_tools=("rbac__get_all_access",),
    ),
    review_user_access=PromptWithTools(
        turns=(
            'Review access permissions for user "{rbac_username}" across all Red Hat applications '
            "to ensure they have appropriate access.",
        ),
        expected_tools=("rbac__get_all_access",),
    ),
)
