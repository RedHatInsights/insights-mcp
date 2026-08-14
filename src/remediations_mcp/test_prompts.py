"""Single source of truth for remediations LLM test prompts."""

from insights_mcp.test_prompts_data import PromptRegistry, PromptWithTools

TOOLSET_TITLE = "Remediations MCP Test Prompts"

PROMPTS = PromptRegistry(
    create_playbook=PromptWithTools(
        turns=("Create remediation playbook for `{cve_id}` on system `{system_id}`",),
        expected_tools=("remediations__create_vuln_playbook",),
    ),
    create_playbook_yaml=PromptWithTools(
        turns=(
            "Create remediation playbook for `{cve_id}` on system `{system_id}` "
            "and give me remediation playbook in `yaml` format",
        ),
        expected_tools=("remediations__create_vuln_playbook",),
    ),
)
