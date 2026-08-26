"""Single source of truth for content-sources LLM test prompts."""

from mcp_llm_eval.data import PromptRegistry, TestScenario

TOOLSET_TITLE = "Content Sources MCP Test Prompts"

PROMPTS = PromptRegistry(
    list_all_repositories=TestScenario(
        turns=("List all repositories from content sources",),
        expected_tools=("content-sources__list_repositories",),
    ),
    enabled_rpm_repositories=TestScenario(
        turns=("Show me repositories that are enabled and have content type 'rpm'",),
        expected_tools=("content-sources__list_repositories",),
    ),
    search_name_rhel=TestScenario(
        turns=("Find repositories with 'rhel' in the name",),
        expected_tools=("content-sources__list_repositories",),
    ),
    first_five_repositories=TestScenario(
        turns=("Show me the first 5 repositories",),
        expected_tools=("content-sources__list_repositories",),
    ),
    arch_x86_64=TestScenario(
        turns=("List repositories for x86_64 architecture",),
        expected_tools=("content-sources__list_repositories",),
    ),
    rhel9_repositories=TestScenario(
        turns=("Show repositories for RHEL 9",),
        expected_tools=("content-sources__list_repositories",),
    ),
    red_hat_origin=TestScenario(
        turns=("List only Red Hat repositories",),
        expected_tools=("content-sources__list_repositories",),
    ),
    url_baseos=TestScenario(
        turns=("Find repositories with 'baseos' in the URL",),
        expected_tools=("content-sources__list_repositories",),
    ),
    combined_filters=TestScenario(
        turns=("Show enabled RPM repositories for x86_64 architecture with 'appstream' in the name",),
        expected_tools=("content-sources__list_repositories",),
    ),
    disabled_repositories=TestScenario(
        turns=("List all disabled repositories",),
        expected_tools=("content-sources__list_repositories",),
    ),
    large_limit=TestScenario(
        turns=("List repositories with limit 1000",),
        expected_tools=("content-sources__list_repositories",),
    ),
    nonexistent_name=TestScenario(
        turns=("Find repositories with name 'nonexistent-repo'",),
        expected_tools=("content-sources__list_repositories",),
    ),
    analyze_by_content_type=TestScenario(
        turns=("Analyze my repository setup - show me all repositories grouped by content type",),
        expected_tools=("content-sources__list_repositories",),
    ),
    repository_health=TestScenario(
        turns=("Check the health of my repositories - show me disabled repositories and any with errors",),
        expected_tools=("content-sources__list_repositories",),
    ),
    full_inventory=TestScenario(
        turns=("Give me a complete inventory of all my content sources repositories",),
        expected_tools=("content-sources__list_repositories",),
    ),
)
