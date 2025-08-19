"""Red Hat Insights Remediations MCP Server.

MCP server for remediation playbooks via Red Hat Insights API.
Provides tools to create Ansible Remediation Playbooks to fix systems connected to Insights.
"""

import random
from typing import Any
from insights_mcp.mcp import InsightsMCP


mcp = InsightsMCP(
    name="Insights Remediations MCP Server",
    toolset_name="remediations",
    api_path="api/remediations/v1",
    instructions="""
    This server provides tools to create Ansible Remediation Playbooks to fix systems connected to Insights.
    You can create playbooks for different issues, such as vulnerability mitigation or applying InsightsAdvisor recommendations.

    [INSTRUCTION] Be communicative. Ask user if they want to get a link to the playbook or to get the YAML content.
    Playbooks in YAML format MUST be returned as is without any changes.
    """,
)


@mcp.tool()
async def create_vulnerability_playbook(playbook_name: str, cves: list[str], uuids: list[str]) -> dict[str, Any] | str:
    """Create remediation playbook for given CVEs on given systems to mitigate vulnerabilities.

    Don't process the playbook. You MUST return the YAML as is.
    Ask user if they want to get a link to the playbook or to get the YAML content.
    Inform them about the limitations of the link and that printing the YAML can be slow.

    If user ask for it, you can also respond with a link to the playbook in a format like this:
    ```
    https://console.redhat.com/insights/remediations/{playbook_id}
    ```
    Inform user that they can't see the playbook with user other than Service Account used to create it.
    This limitation is reported at https://issues.redhat.com/browse/RHINENG-20235.
    Therefore to download the playbook, user needs to authenticate with Insights with their Red Hat Service Account.

    Args:
        playbook_name: Name of the playbook. Example: "Remediation Playbook"
        cves: CVE identifiers. Example: ["CVE-2016-0800", "CVE-2016-0801"]
        uuids: Systems Inventory UUIDs. Example: [123e4567-e89b-12d3-a456-426614174000]
    """

    playbook_name = playbook_name + " mcp-generated-playbook-" + str(random.randint(100000, 999999))
    resolutions_in = {"issues": [f"vulnerabilities:{cve.upper()}" for cve in cves]}
    response = await mcp.insights_client.post("resolutions", json=resolutions_in)
    if isinstance(response, str) or resolutions_in["issues"][0] not in response:
        return response

    resolutions: dict[str, list[dict[str, Any]]] = {"issues": []}
    needs_reboot = False
    for _, value in response.items():
        resolution = value.get("resolutions", [{}])[0]
        needs_reboot = needs_reboot or resolution.get("needs_reboot", False)
        resolutions["issues"].append(
            {"id": value.get("id", ""), "resolution": resolution.get("id", ""), "systems": uuids}
        )
    remediations_in = {"name": playbook_name, "add": resolutions, "auto_reboot": needs_reboot}

    response = await mcp.insights_client.post("remediations", json=remediations_in)
    if isinstance(response, str) or "id" not in response:
        return response

    return await mcp.insights_client.get(f"remediations/{response['id']}/playbook")
