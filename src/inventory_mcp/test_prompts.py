"""Single source of truth for inventory LLM test prompts."""

from insights_mcp.test_prompts_data import PromptRegistry

TOOLSET_TITLE = "Inventory MCP Test Prompts"

PROMPTS = PromptRegistry(
    rhel9_recent_hosts=(
        "List all hosts running RHEL 9 that were last seen in the past day",
        ("inventory__list_hosts",),
    ),
    top_active_hosts=(
        "Show me the top 5 most recently active hosts",
        ("inventory__list_hosts",),
    ),
    host_details_by_name=(
        "Get details for host named '{hostname}'",
        ("inventory__list_hosts", "inventory__find_host_by_name"),
    ),
    stale_host_count=(
        "How many hosts are currently stale?",
        ("inventory__list_hosts",),
    ),
    satellite_tag_filter=(
        "List all hosts with the Satellite tag `{satellite_tag}`",
        ("inventory__list_hosts",),
    ),
    host_system_profiles=(
        "Get the system profile information for hosts with IDs: `{host_ids}`",
        ("inventory__get_host_system_profile",),
    ),
    recent_host_tags=(
        "Get all tags for hosts that were updated in the last 24 hours",
        ("inventory__list_hosts", "inventory__get_host_tags"),
    ),
    fqdn_suffix_filter=(
        "Find all hosts with `FQDN` ending in `.example.com`",
        ("inventory__list_hosts",),
    ),
    enabled_repositories=(
        "Show me all enabled repositories on host `{hostname}`",
        ("inventory__list_hosts", "inventory__get_host_system_profile"),
    ),
    aws_high_memory_hosts=(
        "Find hosts with more than 16GB of memory running on AWS",
        ("inventory__list_hosts",),
    ),
)
