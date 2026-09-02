"""Single source of truth for inventory LLM test prompts."""

from mcp_llm_eval.data import PromptRegistry, PromptWithTools, TestScenario

TOOLSET_TITLE = "Inventory MCP Test Prompts"

PROMPTS = PromptRegistry(
    rhel9_recent_hosts=TestScenario(
        turns=(
            PromptWithTools(
                prompt="List all hosts running RHEL 9 that were last seen in the past day",
                expected_tools=("inventory__list_hosts",),
            ),
        ),
    ),
    top_active_hosts=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Show me the top 5 most recently active hosts",
                expected_tools=("inventory__list_hosts",),
            ),
        ),
    ),
    host_details_by_name=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Get details for host named '{hostname}'",
                expected_tools=("inventory__list_hosts", "inventory__find_host_by_name"),
            ),
        ),
    ),
    stale_host_count=TestScenario(
        turns=(
            PromptWithTools(
                prompt="How many hosts are currently stale?",
                expected_tools=("inventory__list_hosts",),
            ),
        ),
    ),
    satellite_tag_filter=TestScenario(
        turns=(
            PromptWithTools(
                prompt="List all hosts with the Satellite tag `{satellite_tag}`",
                expected_tools=("inventory__list_hosts",),
            ),
        ),
    ),
    host_system_profiles=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Get the system profile information for hosts with IDs: `{host_ids}`",
                expected_tools=("inventory__get_host_system_profile",),
            ),
        ),
    ),
    recent_host_tags=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Get all tags for hosts that were updated in the last 24 hours",
                expected_tools=("inventory__list_hosts", "inventory__get_host_tags"),
            ),
        ),
    ),
    fqdn_suffix_filter=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Find all hosts with `FQDN` ending in `.example.com`",
                expected_tools=("inventory__list_hosts",),
            ),
        ),
    ),
    enabled_repositories=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Show me all enabled repositories on host `{hostname}`",
                expected_tools=("inventory__list_hosts", "inventory__get_host_system_profile"),
            ),
        ),
    ),
    aws_high_memory_hosts=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Find hosts with more than 16GB of memory running on AWS",
                expected_tools=("inventory__list_hosts",),
            ),
        ),
    ),
)
