"""Single source of truth for content-sources LLM test prompts."""

from insights_mcp.test_prompts_data import PromptRegistry

TOOLSET_TITLE = "Content Sources MCP Test Prompts"

PROMPTS = PromptRegistry(
    list_all_repositories=(
        "List all repositories from content sources",
        ("content-sources__list_repositories",),
    ),
    enabled_rpm_repositories=(
        "Show me repositories that are enabled and have content type 'rpm'",
        ("content-sources__list_repositories",),
    ),
    search_name_rhel=(
        "Find repositories with 'rhel' in the name",
        ("content-sources__list_repositories",),
    ),
    first_five_repositories=(
        "Show me the first 5 repositories",
        ("content-sources__list_repositories",),
    ),
    arch_x86_64=(
        "List repositories for x86_64 architecture",
        ("content-sources__list_repositories",),
    ),
    rhel9_repositories=(
        "Show repositories for RHEL 9",
        ("content-sources__list_repositories",),
    ),
    red_hat_origin=(
        "List only Red Hat repositories",
        ("content-sources__list_repositories",),
    ),
    url_baseos=(
        "Find repositories with 'baseos' in the URL",
        ("content-sources__list_repositories",),
    ),
    combined_filters=(
        "Show enabled RPM repositories for x86_64 architecture with 'appstream' in the name",
        ("content-sources__list_repositories",),
    ),
    disabled_repositories=(
        "List all disabled repositories",
        ("content-sources__list_repositories",),
    ),
    large_limit=(
        "List repositories with limit 1000",
        ("content-sources__list_repositories",),
    ),
    nonexistent_name=(
        "Find repositories with name 'nonexistent-repo'",
        ("content-sources__list_repositories",),
    ),
    analyze_by_content_type=(
        "Analyze my repository setup - show me all repositories grouped by content type",
        ("content-sources__list_repositories",),
    ),
    repository_health=(
        "Check the health of my repositories - show me disabled repositories and any with errors",
        ("content-sources__list_repositories",),
    ),
    full_inventory=(
        "Give me a complete inventory of all my content sources repositories",
        ("content-sources__list_repositories",),
    ),
)
