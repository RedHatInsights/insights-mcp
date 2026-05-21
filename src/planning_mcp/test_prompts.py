"""Single source of truth for planning LLM test prompts."""

from insights_mcp.test_prompts_data import PromptRegistry

TOOLSET_TITLE = "Planning MCP Test Prompts"

PROMPTS = PromptRegistry(
    upcoming_changes_all=(
        "Show me all upcoming package changes in the roadmap.",
        ("planning__get_upcoming_changes",),
    ),
    upcoming_changes_rhel94=(
        "What upcoming changes are planned for RHEL 9.4?",
        ("planning__get_upcoming_changes",),
    ),
    upcoming_deprecations=(
        "Which packages are going to be deprecated next year?",
        ("planning__get_upcoming_changes",),
    ),
    upcoming_roadmap_rhel89=(
        "Help me understand the main roadmap changes that might affect our RHEL 8 and 9 systems.",
        ("planning__get_upcoming_changes",),
    ),
    nodejs_streams=(
        "What versions of Node.js are available across RHEL 8, 9, and 10?",
        ("planning__get_appstreams_lifecycle",),
    ),
    rhel9_modules_lifecycle=(
        "Show me the detailed lifecycle of all modules available on RHEL 9.",
        ("planning__get_appstreams_lifecycle",),
    ),
    postgresql_rhel8_support=(
        "Is the 'postgresql' package supported on RHEL 8, and when does it expire?",
        ("planning__get_appstreams_lifecycle",),
    ),
    rhel_lifecycle_all=(
        "Give me complete list of the available RHEL versions and their support status.",
        ("planning__get_rhel_lifecycle",),
    ),
    rhel101_support_status=(
        "What is the support status of RHEL 10.1?",
        ("planning__get_rhel_lifecycle",),
    ),
    rhel_retirements_next_year=(
        "Which RHEL version are going to be retired next year?",
        ("planning__get_rhel_lifecycle",),
    ),
    rhel88_actions=(
        "I'm using RHEL 8.8. Are there any actions regarding my RHEL version I should take?",
        ("planning__get_rhel_lifecycle",),
    ),
    relevant_upcoming_all=(
        "Show me all relevant upcoming changes for my systems.",
        ("planning__get_relevant_upcoming",),
    ),
    relevant_upcoming_rhel9=(
        "What relevant upcoming changes affect my RHEL 9 systems?",
        ("planning__get_relevant_upcoming",),
    ),
    relevant_upcoming_rhel92=(
        "Show me relevant upcoming changes for my RHEL 9.2 systems",
        ("planning__get_relevant_upcoming",),
    ),
    relevant_appstreams_all=(
        "What application streams are relevant to my systems, including related successor streams?",
        ("planning__get_relevant_appstreams",),
    ),
    relevant_appstreams_installed_only=(
        "Show me only the application streams that are actually installed on my systems, without any suggestions.",
        ("planning__get_relevant_appstreams",),
    ),
    relevant_appstreams_rhel9=(
        "What application streams are relevant to my RHEL 9 systems and any related successor streams",
        ("planning__get_relevant_appstreams",),
    ),
    relevant_appstreams_rhel92=(
        "Show me the appstreams relevant to my RHEL 9.2 systems and any related successor streams",
        ("planning__get_relevant_appstreams",),
    ),
    appstream_upgrade_opportunities=(
        "Are there newer versions of the application streams I'm using that I should consider upgrading to?",
        ("planning__get_relevant_appstreams",),
    ),
    nodejs_inventory_support=(
        "Is the Node.js version in our inventory still supported, and are there newer options available?",
        ("planning__get_relevant_appstreams",),
    ),
    relevant_rhel_lifecycle_all=(
        "What RHEL versions are currently running in my environment and when do they go out of support?",
        ("planning__get_relevant_rhel_lifecycle",),
    ),
    relevant_rhel_lifecycle_rhel8=(
        "Show me the lifecycle status of my RHEL 8 systems.",
        ("planning__get_relevant_rhel_lifecycle",),
    ),
    relevant_rhel_lifecycle_rhel92=(
        "Show me the lifecycle status of my RHEL 9.2 systems?",
        ("planning__get_relevant_rhel_lifecycle",),
    ),
    rhel9_upgrade_targets=(
        "What RHEL 9 minor versions could I upgrade my systems to that are still supported?",
        ("planning__get_relevant_rhel_lifecycle",),
    ),
)
