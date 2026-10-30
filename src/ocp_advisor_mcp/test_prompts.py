"""Single source of truth for OCP Advisor LLM test prompts."""

from tests.mcp_llm_eval.data import PromptWithTools, TestScenario, TestScenarioRegistry

TOOLSET_TITLE = "OCP Advisor MCP Test Prompts"

PROMPTS = TestScenarioRegistry(
    deployed_rules_version=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Get the deployed ccx-ocp-rules version for OCP Advisor in production.",
                expected_tools=("ocp-advisor__get_info",),

            ),
        ),
    ),
    verify_rules_release=TestScenario(
        turns=(
            PromptWithTools(
                prompt=(
                    "Verify the latest OCP Advisor rules release was deployed to production "
                    "and show the Content Service commit and build metadata."
                ),
                expected_tools=("ocp-advisor__get_info",),

            ),
        ),
    ),
    production_stack_health=TestScenario(
        turns=(
            PromptWithTools(
                prompt=(
                    "Check that the OCP Advisor production backend is healthy across Smart Proxy, "
                    "Aggregator, and Content Service."
                ),
                expected_tools=("ocp-advisor__get_info",),

            ),
        ),
    ),
    list_available_clusters=TestScenario(
        turns=(
            PromptWithTools(
                prompt=(
                    "List the OpenShift clusters visible to OCP Advisor and summarize their recommendation hit counts "
                    "and risk levels."
                ),
                expected_tools=("ocp-advisor__list_clusters",),
                forbidden_tools=("rbac__explain_access_denied",),

            ),
        ),
    ),
    cluster_recommendations=TestScenario(
        turns=(
            PromptWithTools(
                prompt=(
                    "Show me the Insights Advisor recommendations for OpenShift cluster "
                    "11111111-2222-3333-4444-555555555555, including the risk level and what I should do "
                    "about each finding."
                ),
                expected_tools=("ocp-advisor__get_recommendations",),
                forbidden_tools=("rbac__explain_access_denied",),
                turn_criteria=(
                    "The response should list the cluster's recommendations with their risk "
                    "level and a suggested action drawn from the rendered resolution text. "
                    "Recommendation guidance must be presented as rendered prose: the response "
                    "must not contain raw DoT.js template syntax (e.g. {{ }} or {{= ... }}), "
                    "and fields whose rendering failed (rendering status failed) must not be "
                    "presented as rendered guidance. The response must not be raw JSON."
                ),
            ),
        ),
    ),
    cluster_recommendations_include_disabled=TestScenario(
        turns=(
            PromptWithTools(
                prompt=(
                    "Include disabled recommendations when listing the findings for OpenShift cluster "
                    "11111111-2222-3333-4444-555555555555."
                ),
                expected_tools=("ocp-advisor__get_recommendations",),
                forbidden_tools=("rbac__explain_access_denied",),
                expected_args={
                    "ocp-advisor__get_recommendations": [{"include_disabled": True}],
                },
                turn_criteria=(
                    "The response should indicate that disabled recommendations are included "
                    "in the listing, and identify which findings are disabled when any are "
                    "present. Recommendation guidance must be presented as rendered prose, "
                    "not raw DoT.js template syntax (e.g. {{ }} or {{= ... }})."
                ),
            ),
        ),
    ),
    dvo_namespaces_overview=TestScenario(
        turns=(
            PromptWithTools(
                prompt=(
                    "Which namespaces have DVO workload recommendations and how severe are they?"
                ),
                expected_tools=("ocp-advisor__get_dvo_namespaces",),
                forbidden_tools=("rbac__explain_access_denied",),
                turn_criteria=(
                    "The response should summarize the namespaces with DVO workload "
                    "recommendations, including recommendation counts and severity levels. "
                    "Namespace names are often empty in the data; the response must not invent "
                    "namespace names and should reference namespaces by their cluster and "
                    "namespace UUIDs when no display name exists. The response must not be raw JSON."
                ),
            ),
        ),
    ),
    dvo_recommendations_detail=TestScenario(
        turns=(
            PromptWithTools(
                prompt=(
                    "Show the DVO recommendations for namespace aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee "
                    "of cluster 11111111-2222-3333-4444-555555555555, including the affected workloads."
                ),
                expected_tools=("ocp-advisor__get_dvo_recommendations",),
                forbidden_tools=("rbac__explain_access_denied",),
                turn_criteria=(
                    "The response should describe the DVO recommendations for the namespace "
                    "with their severity and the affected workload objects (kind and name or "
                    "identifier). Guidance must be presented as rendered prose: the response "
                    "must not contain raw DoT.js template syntax (e.g. {{ }} or {{= ... }}), "
                    "and fields flagged with a failed rendering status must not be presented "
                    "as rendered guidance. The response must not be raw JSON."
                ),
            ),
        ),
    ),
    upgrade_risk_for_cluster=TestScenario(
        turns=(
            PromptWithTools(
                prompt=(
                    "For clusters 11111111-2222-3333-4444-555555555555 and "
                    "22222222-3333-4444-5555-666666666666, get the upgrade-risk predictions and "
                    "explain any alerts or operator conditions that would block an upgrade."
                ),
                expected_tools=("ocp-advisor__get_upgrade_risk",),
                forbidden_tools=("rbac__explain_access_denied",),
            ),
        ),
    ),
)
