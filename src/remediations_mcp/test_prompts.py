"""Single source of truth for remediations LLM test prompts."""

from insights_mcp.test_prompts_data import PromptRegistry

TOOLSET_TITLE = "Remediations MCP Test Prompts"

PROMPTS = PromptRegistry(
    create_playbook=(
        "Create remediation playbook for `{cve_id}` on system `{system_id}`",
        ("remediations__create_vuln_playbook",),
    ),
    create_playbook_yaml=(
        "Create remediation playbook for `{cve_id}` on system `{system_id}` "
        "and give me remediation playbook in `yaml` format",
        ("remediations__create_vuln_playbook",),
    ),
)
