"""Single source of truth for RBAC LLM test prompts."""

from insights_mcp.test_prompts_data import PromptRegistry

TOOLSET_TITLE = "RBAC MCP Test Prompts"

PROMPTS = PromptRegistry(
    my_insights_permissions=(
        "please check my insights permissions are there any missing for insights-mcp?",
        ("rbac__get_all_access",),
    ),
    user_access_across_apps=(
        'Show me access permissions for user "{rbac_username}" across all applications',
        ("rbac__get_all_access",),
    ),
    paginated_access=(
        "Get the first 50 access records across all applications",
        ("rbac__get_all_access",),
    ),
    service_account_access=(
        'What access permissions does service account "{rbac_username}" have across all Red Hat applications?',
        ("rbac__get_all_access",),
    ),
    debug_my_permissions=(
        "I can't access certain features in Red Hat services. Show me all my access permissions "
        "across all applications to help debug the issue.",
        ("rbac__get_all_access",),
    ),
    review_user_access=(
        'Review access permissions for user "{rbac_username}" across all Red Hat applications '
        "to ensure they have appropriate access.",
        ("rbac__get_all_access",),
    ),
)
