"""Single source of truth for advisor LLM test prompts."""

from insights_mcp.test_prompts_data import PromptRegistry

TOOLSET_TITLE = "Advisor MCP Test Prompts"

PROMPTS = PromptRegistry(
    top_critical_issues=(
        "Show me the top 5 critical issues on my systems",
        ("advisor__get_active_rules",),
    ),
    kb_article_impact=(
        "I saw a Knowledge Base Article https://access.redhat.com/articles/6464541; "
        "does any of my systems are affected by the issue it describes?",
        ("advisor__get_rule_from_node_id", "advisor__get_active_rules"),
    ),
    auto_remediation_rules=(
        "List all the affected recommendations that have automated solutions available",
        ("advisor__get_active_rules",),
    ),
    rule_details=(
        'Show me the details for the advisor recommendation "{rule_id}"',
        ("advisor__get_rule_details",),
    ),
    rule_affected_systems=(
        'List all the systems affected by the advisor recommendation "{rule_id}"',
        ("advisor__get_hosts_hitting_a_rule", "advisor__get_rule_details"),
    ),
    recommendations_by_tag=(
        "Show me Advisor recommendations for systems tagged 'insights-client/security=strict'.",
        ("advisor__get_active_rules",),
    ),
    recommendations_by_workspace=(
        'Show me Advisor recommendations for systems in the workspace "{workspace}".',
        ("advisor__get_active_rules",),
    ),
    top_impacting_recommendations=(
        "Show me the 10 recommendations that affect the most systems.",
        ("advisor__get_active_rules",),
    ),
    critical_with_playbook=(
        "Show me all 'Critical' or 'Important' security recommendations "
        "that have a playbook available for remediation.",
        ("advisor__get_active_rules",),
    ),
    rhel8_rule_systems=(
        'List me RHEL 8 systems affected by the issue "{rule_id}".',
        ("advisor__get_hosts_details_for_rule", "advisor__get_hosts_hitting_a_rule"),
    ),
    reboot_recommendations=(
        "List recommendations that requires a reboot?",
        ("advisor__get_active_rules",),
    ),
    huge_pages_risk=(
        "Explain the risk associated with the 'Disable Transparent Huge Pages' recommendation.",
        ("advisor__get_rule_details", "advisor__get_active_rules"),
    ),
)
