"""Single source of truth for remediations LLM test prompts."""

from mcp_llm_eval.data import PromptRegistry, PromptWithTools, TestScenario

TOOLSET_TITLE = "Remediations MCP Test Prompts"

PROMPTS = PromptRegistry(
    create_playbook=TestScenario(
        turns=(
            PromptWithTools(
                prompt="Create remediation playbook for `{cve_id}` on system `{system_id}`",
                expected_tools=("remediations__create_vuln_playbook",),
            ),
        ),
    ),
    create_playbook_yaml=TestScenario(
        turns=(
            PromptWithTools(
                prompt=(
                    "Create remediation playbook for `{cve_id}` on system `{system_id}` "
                    "and give me remediation playbook in `yaml` format"
                ),
                expected_tools=("remediations__create_vuln_playbook",),
            ),
        ),
    ),
)
