"""Single source of truth for planning LLM test prompts."""

from mcp_llm_eval.data import PromptRegistry, PromptWithTools

TOOLSET_TITLE = "Planning MCP Test Prompts"

PROMPTS = PromptRegistry(
    upcoming_changes_all=PromptWithTools(
        turns=("Show me all upcoming package changes in the roadmap.",),
        expected_tools=("planning__get_upcoming_changes",),
    ),
    upcoming_changes_rhel94=PromptWithTools(
        turns=("What upcoming changes are planned for RHEL 9.4?",),
        expected_tools=("planning__get_upcoming_changes",),
    ),
    upcoming_deprecations=PromptWithTools(
        turns=("Which packages are going to be deprecated next year?",),
        expected_tools=("planning__get_upcoming_changes",),
    ),
    upcoming_roadmap_rhel89=PromptWithTools(
        turns=("Help me understand the main roadmap changes that might affect our RHEL 8 and 9 systems.",),
        expected_tools=("planning__get_upcoming_changes",),
    ),
    nodejs_streams=PromptWithTools(
        turns=("What versions of Node.js are available across RHEL 8, 9, and 10?",),
        expected_tools=("planning__get_appstreams_lifecycle",),
    ),
    rhel9_modules_lifecycle=PromptWithTools(
        turns=("Show me the detailed lifecycle of all modules available on RHEL 9.",),
        expected_tools=("planning__get_appstreams_lifecycle",),
    ),
    postgresql_rhel8_support=PromptWithTools(
        turns=("Is the 'postgresql' package supported on RHEL 8, and when does it expire?",),
        expected_tools=("planning__get_appstreams_lifecycle",),
    ),
    rhel_lifecycle_all=PromptWithTools(
        turns=("Give me complete list of the available RHEL versions and their support status.",),
        expected_tools=("planning__get_rhel_lifecycle",),
    ),
    rhel101_support_status=PromptWithTools(
        turns=("What is the support status of RHEL 10.1?",),
        expected_tools=("planning__get_rhel_lifecycle",),
    ),
    rhel_retirements_next_year=PromptWithTools(
        turns=("Which RHEL version are going to be retired next year?",),
        expected_tools=("planning__get_rhel_lifecycle",),
    ),
    rhel88_actions=PromptWithTools(
        turns=("I'm using RHEL 8.8. Are there any actions regarding my RHEL version I should take?",),
        expected_tools=("planning__get_rhel_lifecycle",),
    ),
    relevant_upcoming_all=PromptWithTools(
        turns=("Show me all relevant upcoming changes for my systems.",),
        expected_tools=("planning__get_relevant_upcoming",),
    ),
    relevant_upcoming_rhel9=PromptWithTools(
        turns=("What relevant upcoming changes affect my RHEL 9 systems?",),
        expected_tools=("planning__get_relevant_upcoming",),
    ),
    relevant_upcoming_rhel92=PromptWithTools(
        turns=("Show me relevant upcoming changes for my RHEL 9.2 systems",),
        expected_tools=("planning__get_relevant_upcoming",),
    ),
    relevant_appstreams_all=PromptWithTools(
        turns=("What application streams are relevant to my systems, including related successor streams?",),
        expected_tools=("planning__get_relevant_appstreams",),
    ),
    relevant_appstreams_installed_only=PromptWithTools(
        turns=(
            "Show me only the application streams that are actually installed on my systems, without any suggestions.",
        ),
        expected_tools=("planning__get_relevant_appstreams",),
    ),
    relevant_appstreams_rhel9=PromptWithTools(
        turns=("What application streams are relevant to my RHEL 9 systems and any related successor streams",),
        expected_tools=("planning__get_relevant_appstreams",),
    ),
    relevant_appstreams_rhel92=PromptWithTools(
        turns=("Show me the appstreams relevant to my RHEL 9.2 systems and any related successor streams",),
        expected_tools=("planning__get_relevant_appstreams",),
    ),
    appstream_upgrade_opportunities=PromptWithTools(
        turns=("Are there newer versions of the application streams I'm using that I should consider upgrading to?",),
        expected_tools=("planning__get_relevant_appstreams",),
    ),
    nodejs_inventory_support=PromptWithTools(
        turns=("Is the Node.js version in our inventory still supported, and are there newer options available?",),
        expected_tools=("planning__get_relevant_appstreams",),
    ),
    relevant_rhel_lifecycle_all=PromptWithTools(
        turns=("What RHEL versions are currently running in my environment and when do they go out of support?",),
        expected_tools=("planning__get_relevant_rhel_lifecycle",),
    ),
    relevant_rhel_lifecycle_rhel8=PromptWithTools(
        turns=("Show me the lifecycle status of my RHEL 8 systems.",),
        expected_tools=("planning__get_relevant_rhel_lifecycle",),
    ),
    relevant_rhel_lifecycle_rhel92=PromptWithTools(
        turns=("Show me the lifecycle status of my RHEL 9.2 systems?",),
        expected_tools=("planning__get_relevant_rhel_lifecycle",),
    ),
    rhel9_upgrade_targets=PromptWithTools(
        turns=("What RHEL 9 minor versions could I upgrade my systems to that are still supported?",),
        expected_tools=("planning__get_relevant_rhel_lifecycle",),
    ),
)
