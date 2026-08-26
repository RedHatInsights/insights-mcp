"""Single source of truth for advisor LLM test prompts."""

from mcp_llm_eval.data import PromptRegistry, TestScenario

TOOLSET_TITLE = "Advisor MCP Test Prompts"

PROMPTS = PromptRegistry(
    top_critical_issues=TestScenario(
        turns=("Show me the top 5 critical issues on my systems",),
        expected_tools=("advisor__get_active_rules",),
    ),
    kb_article_impact=TestScenario(
        turns=(
            "I saw a Knowledge Base Article https://access.redhat.com/articles/6464541; "
            "does any of my systems are affected by the issue it describes?",
        ),
        expected_tools=("advisor__get_rule_from_node_id", "advisor__get_active_rules"),
    ),
    auto_remediation_rules=TestScenario(
        turns=("List all the affected recommendations that have automated solutions available",),
        expected_tools=("advisor__get_active_rules",),
    ),
    rule_details=TestScenario(
        turns=('Show me the details for the advisor recommendation "{rule_id}"',),
        expected_tools=("advisor__get_rule_details",),
    ),
    rule_affected_systems=TestScenario(
        turns=('List all the systems affected by the advisor recommendation "{rule_id}"',),
        expected_tools=(
            "advisor__get_hosts_hitting_a_rule",
            "advisor__get_hosts_details_for_rule",
            "advisor__get_rule_details",
        ),
    ),
    recommendations_by_tag=TestScenario(
        turns=("Show me Advisor recommendations for systems tagged 'insights-client/security=strict'.",),
        expected_tools=("advisor__get_active_rules",),
    ),
    recommendations_by_workspace=TestScenario(
        turns=('Show me Advisor recommendations for systems in the workspace "{workspace}".',),
        expected_tools=("advisor__get_active_rules",),
    ),
    top_impacting_recommendations=TestScenario(
        turns=("Show me the 10 recommendations that affect the most systems.",),
        expected_tools=("advisor__get_active_rules",),
    ),
    critical_with_playbook=TestScenario(
        turns=(
            "Show me all 'Critical' or 'Important' security recommendations "
            "that have a playbook available for remediation.",
        ),
        expected_tools=("advisor__get_active_rules",),
    ),
    rhel8_rule_systems=TestScenario(
        turns=('List me RHEL 8 systems affected by the issue "{rule_id}".',),
        expected_tools=("advisor__get_hosts_details_for_rule", "advisor__get_hosts_hitting_a_rule"),
    ),
    reboot_recommendations=TestScenario(
        turns=("List recommendations that requires a reboot?",),
        expected_tools=("advisor__get_active_rules",),
    ),
    huge_pages_risk=TestScenario(
        turns=("Explain the risk associated with the 'Disable Transparent Huge Pages' recommendation.",),
        expected_tools=("advisor__get_rule_by_text_search", "advisor__get_active_rules"),
    ),
)
