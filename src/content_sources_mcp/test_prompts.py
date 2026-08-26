"""Single source of truth for content-sources LLM test prompts."""

from mcp_llm_eval.data import PromptWithTools, TestScenario, TestScenarioRegistry

TOOLSET_TITLE = "Content Sources MCP Test Prompts"

PROMPTS = TestScenarioRegistry(
    list_all_repositories=TestScenario(
        turns=(
            PromptWithTools(
                prompt="List all repositories from content sources",
                expected_tools=("content-sources__list_repositories",),
            ),
        ),
    ),
    enabled_rpm_repositories=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Show me repositories that are enabled and have content type 'rpm'",
                expected_tools=("content-sources__list_repositories",),
            ),
        ),
    ),
    search_name_rhel=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Find repositories with 'rhel' in the name",
                expected_tools=("content-sources__list_repositories",),
            ),
        ),
    ),
    first_five_repositories=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Show me the first 5 repositories",
                expected_tools=("content-sources__list_repositories",),
            ),
        ),
    ),
    arch_x86_64=TestScenario(
        turns=(
            PromptWithTools(
                prompt="List repositories for x86_64 architecture",
                expected_tools=("content-sources__list_repositories",),
            ),
        ),
    ),
    rhel9_repositories=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Show repositories for RHEL 9",
                expected_tools=("content-sources__list_repositories",),
            ),
        ),
    ),
    red_hat_origin=TestScenario(
        turns=(
            PromptWithTools(
                prompt="List only Red Hat repositories",
                expected_tools=("content-sources__list_repositories",),
            ),
        ),
    ),
    url_baseos=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Find repositories with 'baseos' in the URL",
                expected_tools=("content-sources__list_repositories",),
            ),
        ),
    ),
    combined_filters=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Show enabled RPM repositories for x86_64 architecture with 'appstream' in the name",
                expected_tools=("content-sources__list_repositories",),
            ),
        ),
    ),
    disabled_repositories=TestScenario(
        turns=(
            PromptWithTools(
                prompt="List all disabled repositories",
                expected_tools=("content-sources__list_repositories",),
            ),
        ),
    ),
    large_limit=TestScenario(
        turns=(
            PromptWithTools(
                prompt="List repositories with limit 1000",
                expected_tools=("content-sources__list_repositories",),
            ),
        ),
    ),
    nonexistent_name=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Find repositories with name 'nonexistent-repo'",
                expected_tools=("content-sources__list_repositories",),
            ),
        ),
    ),
    analyze_by_content_type=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Analyze my repository setup - show me all repositories grouped by content type",
                expected_tools=("content-sources__list_repositories",),
            ),
        ),
    ),
    repository_health=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Check the health of my repositories - show me disabled repositories and any with errors",
                expected_tools=("content-sources__list_repositories",),
            ),
        ),
    ),
    full_inventory=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Give me a complete inventory of all my content sources repositories",
                expected_tools=("content-sources__list_repositories",),
            ),
        ),
    ),
)
