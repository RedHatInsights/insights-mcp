"""Single source of truth for advisor LLM test prompts."""

from tests.mcp_llm_eval.data import PromptWithTools, TestScenario, TestScenarioRegistry

TOOLSET_TITLE = "Advisor MCP Test Prompts"

PROMPTS = TestScenarioRegistry(
    top_critical_issues=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Show me the top 5 critical issues on my systems",
                expected_tools=("advisor__get_active_rules",),
                forbidden_tools=("rbac__explain_access_denied",),
            ),
        ),
    ),
    kb_article_impact=TestScenario(
        turns=(
            PromptWithTools(
                prompt=(
                    "I saw a Knowledge Base Article https://access.redhat.com/articles/6464541; "
                    "does any of my systems are affected by the issue it describes?"
                ),
                required_tools=("advisor__get_rule_from_node_id",),
                expected_tools=(
                    "advisor__get_hosts_hitting_a_rule",
                    "advisor__get_hosts_details_for_rule",
                    "advisor__get_active_rules",
                ),
                forbidden_tools=("rbac__explain_access_denied",),
            ),
        ),
        threshold=0,
    ),
    auto_remediation_rules=TestScenario(
        turns=(
            PromptWithTools(
                prompt="List all the affected recommendations that have automated solutions available",
                expected_tools=("advisor__get_active_rules",),
                forbidden_tools=("rbac__explain_access_denied",),
            ),
        ),
    ),
    rule_details=TestScenario(
        turns=(
            PromptWithTools(
                prompt='Show me the details for the advisor recommendation "{rule_id}"',
                expected_tools=("advisor__get_rule_details",),
                forbidden_tools=("rbac__explain_access_denied",),
            ),
        ),
    ),
    rule_affected_systems=TestScenario(
        turns=(
            PromptWithTools(
                prompt='List all the systems affected by the advisor recommendation "{rule_id}" and show the details',
                expected_tools=(
                    "advisor__get_hosts_hitting_a_rule",
                    "advisor__get_hosts_details_for_rule",
                    "advisor__get_rule_details",
                ),
                forbidden_tools=("rbac__explain_access_denied",),
            ),
        ),
        threshold=0,
    ),
    recommendations_by_tag=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Show me Advisor recommendations for systems tagged 'insights-client/security=strict'.",
                expected_tools=("advisor__get_active_rules",),
                forbidden_tools=("rbac__explain_access_denied",),
            ),
        ),
    ),
    recommendations_by_workspace=TestScenario(
        turns=(
            PromptWithTools(
                prompt='Show me Advisor recommendations for systems in the workspace "{workspace}".',
                expected_tools=("advisor__get_active_rules",),
                forbidden_tools=("rbac__explain_access_denied",),
            ),
        ),
    ),
    top_impacting_recommendations=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Show me the 10 recommendations that affect the most systems.",
                expected_tools=("advisor__get_active_rules",),
                forbidden_tools=("rbac__explain_access_denied",),
            ),
        ),
    ),
    critical_with_playbook=TestScenario(
        turns=(
            PromptWithTools(
                prompt=(
                    "Show me all 'Critical' or 'Important' security recommendations "
                    "that have a playbook available for remediation."
                ),
                expected_tools=("advisor__get_active_rules",),
                forbidden_tools=("rbac__explain_access_denied",),
            ),
        ),
    ),
    rhel8_rule_systems=TestScenario(
        turns=(
            PromptWithTools(
                prompt='List me RHEL 8 systems affected by the issue "{rule_id}".',
                expected_tools=("advisor__get_hosts_details_for_rule", "advisor__get_hosts_hitting_a_rule"),
                forbidden_tools=("rbac__explain_access_denied",),
            ),
        ),
        threshold=0,
    ),
    reboot_recommendations=TestScenario(
        turns=(
            PromptWithTools(
                prompt="List recommendations that requires a reboot?",
                expected_tools=("advisor__get_active_rules",),
                forbidden_tools=("rbac__explain_access_denied",),
            ),
        ),
    ),
    huge_pages_risk=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Explain the risk associated with the 'Disable Transparent Huge Pages' recommendation.",
                required_tools=("advisor__get_rule_by_text_search",),
                expected_tools=(
                    "advisor__get_active_rules",
                    "advisor__get_rule_details",
                    "advisor__get_rule_by_text_search",
                ),
                forbidden_tools=("rbac__explain_access_denied",),
            ),
        ),
        threshold=0,
    ),
)
