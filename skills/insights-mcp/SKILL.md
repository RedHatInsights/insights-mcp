---
name: insights-mcp
description: Red Hat Insights MCP tools via insights-mcp-cli subcommands.
metadata:
  openclaw:
    emoji: "🔧"
    homepage: https://github.com/RedHatInsights/insights-mcp
    requires:
      bins: ["insights-mcp-cli"]
      env: ["INSIGHTS_CLIENT_ID", "INSIGHTS_CLIENT_SECRET"]
---

# server_cli CLI

## Tool Commands

### get_mcp_version

Get the version of the Red Hat Insights MCP server.
    Always call this if the user asks for the version of the Red Hat Insights MCP server.
    or when there is an API or authentication issue.
    Present the comparison URL to the user.

```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool get_mcp_version
```

### image-builder__get_openapi

Get OpenAPI spec. Use this to get details e.g for a new blueprint

        🟢 CALL IMMEDIATELY - No information gathering required.

        Optional parameters:
        - **endpoints**: Comma-separated endpoint specs (like `GET:/blueprints,POST:/blueprints`).
          When provided, the returned OpenAPI is minimized to only the selected paths and their transitive
          component references. Use this only to prepare payloads for `create_blueprint` or `update_blueprint`.

        Returns:
            OpenAPI specification JSON (possibly reduced when 'endpoints' is provided)

        Raises:
            Exception: If the image-builder connection fails.


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool image-builder__get_openapi --endpoints <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--endpoints` | string | no | Comma-separated list of endpoint specs to reduce the spec, e.g. 'GET:/blueprints,POST:/blueprints'. Only needed for create_blueprint/update_blueprint. (JSON string) |

### image-builder__get_blueprints

Show user's image blueprints (saved image templates/configurations for
        Linux distributions, packages, users).

        🟢 CALL IMMEDIATELY - No information gathering required.


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool image-builder__get_blueprints --limit <value> --offset <value> --search-string <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--limit` | integer | no | Maximum number of items to return (use 7 as default) |
| `--offset` | integer | no | Number of items to skip when paging (use 0 as default) |
| `--search-string` | string | no | Substring to search for in the name (JSON string) |

### image-builder__get_blueprint_details

Get blueprint details.

        🟢 CALL IMMEDIATELY - No information gathering required.

        Returns:
            Blueprint details

        Raises:
            Exception: If the image-builder connection fails.


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool image-builder__get_blueprint_details --blueprint-identifier <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--blueprint-identifier` | string | yes | The UUID, name or reply_id to query |

### image-builder__get_composes

Get a list of all image builds (composes) with their UUIDs and basic status.

        **ALWAYS USE THIS FIRST** when checking image build status or finding builds.
        This returns the UUID needed for get_compose_details.
        🟢 CALL IMMEDIATELY - No information gathering required.

        Common uses:
        - Check status of recent builds → call this first
        - Find your latest build → call this first
        - Get any build information → call this first
        Ask the user if they want to get more composes and adapt "offset" accordingly.

        You can also provide this link so the user can check directly in the UI:
        https://console.redhat.com/insights/image-builder

        Returns:
            List of composes with:
            - uuid: The unique identifier (REQUIRED for get_compose_details)
            - name: Blueprint name used
            - status: Current build status
            - created_at: When the build started

        Example response:
        [
            {
                "uuid": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "name": "my-rhel-image",
                "status": "RUNNING",
                "created_at": "2025-01-18T10:30:00Z"
            }
        ]


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool image-builder__get_composes --limit <value> --offset <value> --search-string <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--limit` | integer | no | Maximum number of items to return (use 7 as default) |
| `--offset` | integer | no | Number of items to skip when paging (use 0 as default) |
| `--search-string` | string | no | Substring to search for in the name (JSON string) |

### image-builder__get_compose_details

Get detailed information about a specific image build.

        ⚠️ REQUIRES: You MUST have the compose UUID from get_composes() first.
        ⚠️ NEVER call this with generic terms like "latest", "recent", or "my build"
        🟢 CALL IMMEDIATELY - No information gathering required.

        Process:
        1. User asks about build status → call get_composes()
        2. Find the desired compose and copy its UUID
        3. Call this function with that exact UUID

        Returns:
            Detailed compose information including:
            - Full status and progress
            - Error messages if failed
            - Download URLs if completed
            - Build logs
            - Artifact details


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool image-builder__get_compose_details --compose-identifier <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--compose-identifier` | string | yes | The exact UUID string from get_composes() |

### image-builder__get_distributions

Get the list of distributions available to build images with.

        🟢 CALL IMMEDIATELY - No information gathering required.

        Emphasize that there is support only for Red Hat Enterprise Linux (RHEL) images
        and there only for the latest minor version of each major version.
        Emphasize that Fedora images are "similar" to the upstream but no official versions!
        Emphasize that CentOS Stream is not supported by Red Hat.

        Returns:
            List of distributions


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool image-builder__get_distributions
```

### image-builder__get_org_id

Get the organization ID for RHEL image registration/subscription.

        Purpose: Fetch the organization ID for RHEL image registration.

        When to Use: Always use this tool when enabling registration for Red Hat services in a blueprint.

        CRITICAL NOTE: Never assume or use placeholder organization IDs.
        Always fetch the actual organization ID using this tool.

        Returns:
            The organization ID


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool image-builder__get_org_id
```

### rhsm__get_activation_keys

Get the list of activation keys available to the authenticated user.

🟢 CALL IMMEDIATELY - No information gathering required.

This endpoint returns activation keys that can be used for RHEL system registration.
Activation keys contain subscription and configuration information needed to register
systems with Red Hat Subscription Management.

If the user has more questions about the activation keys,
ask the user to go to https://console.redhat.com/insights/connector/activation-keys

Returns:
    List of activation keys with their details including names, descriptions,
    and associated subscriptions.

```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool rhsm__get_activation_keys --limit <value> --offset <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--limit` | integer | no | Maximum number of activation keys to return (default: 20). |
| `--offset` | integer | no | Number of activation keys to skip for pagination (default: 0). |

### rhsm__get_activation_key

Get a specific activation key by name.

🟢 CALL IMMEDIATELY - No information gathering required.

This endpoint returns details for a specific activation key including its name,
description, service level, role, usage, release version, and additional repositories.

Returns:
    Activation key details including configuration and subscription information.

```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool rhsm__get_activation_key --name <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--name` | string | yes | The name of the activation key to retrieve. |

### vulnerability__get_openapi

Get Red Hat Insights Vulnerability OpenAPI specification in JSON format.

```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool vulnerability__get_openapi
```

### vulnerability__get_cves

Get list of CVEs affecting the account.

This provides an overview of vulnerabilities across your entire system inventory.
Use this endpoint to get an overview of which CVEs are affecting your account,
including some CVE metadata, how many systems are affected by each CVE, and more.
For more info refer to OpenAPI spec

```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool vulnerability__get_cves --filter <value> --limit <value> --offset <value> --sort <value> --cvss-from <value> --cvss-to <value> --impact <value> --rule-presence <value> --known-exploit <value> --advisory-available <value> --affecting-host-type <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--filter` | string | no |  |
| `--limit` | integer | no | Pagination - Maximum number of records per page. |
| `--offset` | integer | no | Pagination - Offset of first record of paginated response. |
| `--sort` | string | no | Attribute sorting. Use `-` prefix to sort in descending order. |
| `--cvss-from` | number | no | Filter based on cvss score, starting from the value. |
| `--cvss-to` | number | no | Filter based on cvss score, up to the value. |
| `--impact` | string | no | Comma separated list of CVE Impact IDs. Example : 5,7.     impact mapping: (0, 'NotSet'), (1, 'None'), (2, 'Low'), (3, 'Medium'), (4, 'Moderate'),                     (5, 'Important'), (6, 'High'), (7, 'Critical') |
| `--rule-presence` | string | no | Comma seprated string with bools. If true shows only CVEs with security rule associated,            if false shows CVEs without rules. true, false shows all. |
| `--known-exploit` | string | no | String of booleans (array of booleans), where true shows CVEs with known exploits,            false shows CVEs without known exploits. |
| `--advisory-available` | string | no | String of booleans (array of booleans), where true shows CVE-system pairs                 with available advisory, false shows CVE-system pairs without available advisory. |
| `--affecting-host-type` | string | no | Comma separated string of values. Controls, whenever CVE has 1 or more                  affecting systems. Value "edge" returns CVEs with one or more vulnerable                  immutable systems, value "rpmdnf" returns CVEs with one or more vulnerable                  conventional systems. Value "none" returns CVEs not affecting systems of any kind.                  Allowed values: "edge", "rpmdnf", "none". |

### vulnerability__get_cve

Get details about specific CVE.

This endpoint returns the CVE identification number, description, scores and other metadata.
The metadata includes the description, CVSS 2/3 Score, CVSS 2/3 attack vector, severity, public date,
modified date, business risk, status, a URL to Red Hat web pages, a list of advisories remediating
the CVE, and information regarding known exploits for the CVE.
For more info refer to OpenAPI spec

```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool vulnerability__get_cve --cve <value> --advisory-available <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--cve` | string | yes | CVE identifier. Example : CVE-2016-0800 |
| `--advisory-available` | string | no | String of booleans (array of booleans), where true shows CVE-system pairs                 with available advisory, false shows CVE-system pairs without available advisory. |

### vulnerability__get_cve_systems

Get list of systems affected by a given CVE.

This is a report of affected systems for a given CVE.
Use this tool to obtain list of all affected systems for a given CVE.
For more info refer to OpenAPI spec

```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool vulnerability__get_cve_systems --cve <value> --filter <value> --limit <value> --offset <value> --sort <value> --system-uuid <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--cve` | string | yes | CVE identifier. Example : CVE-2016-0800 (Required) |
| `--filter` | string | no | Full text filter for the display name of system. |
| `--limit` | integer | no | Pagination - Maximum number of records per page. |
| `--offset` | integer | no | Pagination - Offset of first record of paginated response. |
| `--sort` | string | no | Attribute sorting. Use `-` prefix to sort in descending order. |
| `--system-uuid` | string | no | Filter based on Systems Inventory UUID. (JSON string) |

### vulnerability__get_system_cves

Get list of CVEs affecting a given system.

IMPORTANT: Prefer `get_cves` as `get_cves` can filter for CVEs with available advisories.

This is a report of CVEs affecting a given system.
Use this tool to obtain list of all CVEs affecting a given system.
For more info refer to OpenAPI spec

```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool vulnerability__get_system_cves --system-uuid <value> --filter <value> --limit <value> --offset <value> --sort <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--system-uuid` | string | yes | Systems Inventory UUID. Example : 123e4567-e89b-12d3-a456-426614174000 (Required) |
| `--filter` | string | no | Full text filter for the CVE name. |
| `--limit` | integer | no | Pagination - Maximum number of records per page. |
| `--offset` | integer | no | Pagination - Offset of first record of paginated response. |
| `--sort` | string | no | Attribute sorting. Use `-` prefix to sort in descending order. |

### vulnerability__get_systems

Get list of systems in Red Hat Insights Vulnerability inventory.

List all systems registered in Red Hat Insights Vulnerability service, including information about
their last check-in, system name, workspace name, RHEL version, and number of CVEs affecting them.
This tool shows both affected and not affected systems.
For more info refer to OpenAPI spec

```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool vulnerability__get_systems --filter <value> --limit <value> --offset <value> --sort <value> --group-names <value> --rhel-versions <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--filter` | string | no | Full text filter for the display name of system. |
| `--limit` | integer | no | Pagination - Maximum number of records per page. |
| `--offset` | integer | no | Pagination - Offset of first record of paginated response. |
| `--sort` | string | no | Attribute sorting. Use `-` prefix to sort in descending order. |
| `--group-names` | string | no | Filter based on workspace names. Comma separated list of workspace names. |
| `--rhel-versions` | string | no | Filter based on RHEL versions. Comma separated list of RHEL versions. |

### vulnerability__explain_cves

Explain why CVEs are affecting my environment.

This endpoint returns a detailed explanation of why CVEs are affecting my environment.
It uses VMAAS to explain the CVEs, what packages are affected and why.
Alongside with the information how this CVE can be fixed.
To get the explanation, we need to get the system UUID from the inventory and list of CVEs.
'affected_packages' in 'vmaas' response is a list of packages that are affected by the CVE.

To update affected packages, suggest to use Ansible Remediation Playbook via Remediations MCP tool.

```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool vulnerability__explain_cves --cves <value> --system-uuid <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--cves` | array[string] | yes | CVE identifiers. Example: CVE-2016-0800,CVE-2016-0801 |
| `--system-uuid` | string | yes | System UUID. Example: 123e4567-e89b-12d3-a456-426614174000 |

### advisor__get_active_rules

Get active Advisor Recommendations for your account that help identify issues
        affecting system availability, stability, performance, or security.

        Use filters to find recommendations by impact level, likelihood, systems affected, workspace, tags,
        and automatic remediation availability. Higher impact/likelihood values indicate more critical issues.

        Call examples:
            Standard call: {"impacting": true, "offset": 0, "limit": 20}
            High risk only: {"impacting": true, "impact": "3,4", "likelihood": "3,4"}
            Pagination: {"offset": 20, "limit": 20}
            With automatic remediation: {"has_automatic_remediation": true}
            Security and Performance categories: {"category": "2,4"}
            Reboot required: {"reboot": true}
            Sorted by total risk: {"sort": "-total_risk"}
            For workspaces 'workspace1': {"impacting": true, "groups": "workspace1"}
            For systems tagged 'database-servers': {
                "impacting": true,
                "tags": ["insights-client/group=database-servers"]
            }


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool advisor__get_active_rules --impacting <value> --incident <value> --has-automatic-remediation <value> --impact <value> --likelihood <value> --category <value> --reboot <value> --sort <value> --offset <value> --limit <value> --groups <value> --tags <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--impacting` | string | no | Only show recommendations currently impacting systems. (JSON string) |
| `--incident` | string | no | Only show recommendations that cause incidents. (JSON string) |
| `--has-automatic-remediation` | string | no | Only show recommendations that have a playbook for automatic remediation. (JSON string) |
| `--impact` | string | no | Impact level filter as comma-separated string, Example: '1,2,3'. Accepted values: 1 (Low), 2 (Medium), 3 (High), 4 (Critical). Use only these exact values: 1, 2, 3, or 4. (JSON string) |
| `--likelihood` | string | no | Likelihood level filter as comma-separated string, Example: '1,2,3'. Accepted values: 1 (Low), 2 (Medium), 3 (High), 4 (Very High). Use only these exact values: 1, 2, 3, or 4. (JSON string) |
| `--category` | string | no | Recommendation category filter as comma-separated string, Example: '1,2,3'. Accepted values: 1 (Availability), 2 (Security), 3 (Stability), 4 (Performance).  (JSON string) |
| `--reboot` | string | no | Filter recommendations that require a reboot to fix. (JSON string) |
| `--sort` | string | no | Sort field as comma-separated string. Example: '-total_risk,rule_id'. Available fields: category, description, impact, impacted_count, likelihood, playbook_count, publish_date, resolution_risk, rule_id, total_risk. Use '-' prefix for descending order. |
| `--offset` | integer | no | Pagination offset to skip specified number of results. Used with limit. |
| `--limit` | integer | no | Pagination: Maximum number of results per page. |
| `--groups` | string | no | Filter based on workspace names. Comma separated list of workspace names.Used only when impacting=True. Example: 'workspace1,workspace2' (JSON string) |
| `--tags` | string | no | Filter based on system tags. Accepts a single tag or a comma-separated list.Used only when impacting=True. Tag format: 'namespace/key=value'. Example: 'satellite/group=database-servers,insights-client/security=strict' (JSON string) |

### advisor__get_rule_from_node_id

Find Advisor Recommendations related to a specific Knowledge Base article or solution.

        Use this when you have a Knowledge Base article or solution ID and want to find
        corresponding Advisor Recommendations that provide system-specific remediation steps.

        Call examples:
            Standard call: {"node_id": 123456}


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool advisor__get_rule_from_node_id --node-id <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--node-id` | integer | yes | Node ID of the knowledge base article or solution. Example: 123456 |

### advisor__get_rule_details

Get detailed information about a specific Advisor Recommendation, including
        impact level, likelihood, remediation steps, and related knowledge base articles.

        Call Examples:
            Standard call: {"rule_id": "xfs_with_md_raid_hang|XFS_WITH_MD_RAID_HANG_ISSUE_DEFAULT_KERNEL"}


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool advisor__get_rule_details --rule-id <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--rule-id` | string | yes | Recommendation identifier in format: rule_name\|ERROR_KEY. |

### advisor__get_hosts_hitting_a_rule

Get all RHEL systems affected by a specific Advisor Recommendation.

        Shows which systems in your infrastructure have the issue identified
        by this recommendation. Use this to understand the scope of impact.

        Call Examples:
            Standard call: {"rule_id": "xfs_with_md_raid_hang|XFS_WITH_MD_RAID_HANG_ISSUE_DEFAULT_KERNEL"}


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool advisor__get_hosts_hitting_a_rule --rule-id <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--rule-id` | string | yes | Recommendation identifier in format: rule_name\|ERROR_KEY. |

### advisor__get_hosts_details_for_rule

Get detailed information about RHEL systems affected by a specific Advisor Recommendation.

        Returns paginated system details with comprehensive information about each affected system,
        including system identification, impact metrics, RHEL version, and last seen timestamps.
        Each system entry contains hit counts categorized by severity level and incident status.

        Call examples:
            Standard call: {"rule_id": "xfs_with_md_raid_hang|XFS_WITH_MD_RAID_HANG_ISSUE_DEFAULT_KERNEL"}
            With pagination: {"rule_id": "rule_id", "limit": 20, "offset": 0}
            Filter by RHEL version: {"rule_id": "rule_id", "rhel_version": "9.4"}
            Combined filters: {"rule_id": "rule_id", "limit": 50, "offset": 20, "rhel_version": "8.9"}


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool advisor__get_hosts_details_for_rule --rule-id <value> --limit <value> --offset <value> --rhel-version <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--rule-id` | string | yes | Recommendation identifier in format: rule_name\|ERROR_KEY. |
| `--limit` | integer | no | Pagination: Maximum number of results per page. |
| `--offset` | integer | no | Pagination offset to skip specified number of results. Used with limit. |
| `--rhel-version` | string | no | Filter systems by RHEL version. Accepts a comma-separated string or a list. Allowed values: 6.0-6.10, 7.0-7.10, 8.0-8.10, 9.0-9.8, 10.0-10.2. Example: '9.3,9.4,9.5' (JSON string) |

### advisor__get_rule_by_text_search

Finds Advisor Recommendations that contain an exact text substring.

        Call examples:
            Standard call: {"text": "xfs"}


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool advisor__get_rule_by_text_search --text <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--text` | string | yes | The text substring to search for. Example: 'xfs' |

### advisor__get_recommendations_stats

Show statistics of recommendations across categories and risks.

        Call examples:
            Standard call showing all recommendations: {}
            Statistics for the workspace 'workspace1': {"groups": "workspace1"}
            Statistics for systems tagged 'insights-client/security=strict': {"tags": "insights-client/security=strict"}


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool advisor__get_recommendations_stats --groups <value> --tags <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--groups` | string | no | Filter based on workspace names. Comma separated list of workspace names.Used only when impacting=True. Example: 'workspace1,workspace2' (JSON string) |
| `--tags` | string | no | Filter based on system tags. Accepts a single tag or a comma-separated list.Used only when impacting=True. Tag format: 'namespace/key=value'. Example: 'satellite/group=database-servers,insights-client/security=strict' (JSON string) |

### inventory__list_hosts

List hosts with filtering and sorting options.
CRITICAL: For the 'per_page' parameter, you MUST use a value of 10 on the first call to avoid performance
degradation and context overflow.
Only use a larger value if the user explicitly requests to see more systems at once.

```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool inventory__list_hosts --hostname-or-id <value> --display-name <value> --fqdn <value> --tags <value> --staleness <value> --registered-with <value> --provider-type <value> --updated-start <value> --updated-end <value> --per-page <value> --page <value> --order-by <value> --order-how <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--hostname-or-id` | string | no | Filter by display_name, fqdn, or id (case-insensitive). |
| `--display-name` | string | no | Filter by display name (case-insensitive). |
| `--fqdn` | string | no | Filter by FQDN (case-insensitive). |
| `--tags` | string | no | Filter by tags (e.g., 'ns1/key1=val1,ns2/key2=val2'). |
| `--staleness` | string | no | Filter by staleness status (one of 'fresh', 'stale', 'stale_warning', 'unknown'). |
| `--registered-with` | string | no | Filter by reporter that registered the host. |
| `--provider-type` | string | no | Filter by provider type (e.g., 'aws', 'azure', 'gcp'). |
| `--updated-start` | string | no | Filter hosts updated after this timestamp (RFC3339). |
| `--updated-end` | string | no | Filter hosts updated before this timestamp (RFC3339). |
| `--per-page` | integer | no | Number of hosts to return per page **ALWAYS use the default value of 10 for the first call.** This default is carefully chosen for performance and context management. Only increase this value if the user explicitly asks to see more systems at once  |
| `--page` | integer | no | Page number to return. |
| `--order-by` | string | no | Field to sort by ('display_name', 'updated', 'created'). |
| `--order-how` | string | no | Sort direction ('ASC' or 'DESC'). |

### inventory__get_host_details

Get detailed information for specific hosts by their IDs.

Returns comprehensive host data including identifiers (insights_id, satellite_id, bios_uuid),
display names, network info (IP/MAC addresses), cloud provider details, account/org metadata,
timestamps (created, updated, stale_timestamp), reporter info, groups, facts, and basic
system_profile data.

```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool inventory__get_host_details --host-ids <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--host-ids` | string | yes | Comma-separated list of host IDs (UUIDs) to retrieve. |

### inventory__get_host_system_profile

Get detailed system profile information for specific hosts.

Returns comprehensive hardware and software configuration data including CPU details
(model, count, cores per socket), memory info (system_memory_bytes), infrastructure
details (type, vendor), network interfaces, disk devices, BIOS information, and
various system state data. For RHEL hosts, also includes software information such as
enabled repositories, installed packages, and enabled services. This provides the most
detailed technical specifications for each host.

```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool inventory__get_host_system_profile --host-ids <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--host-ids` | string | no | Comma-separated list of host IDs (UUIDs) to get system profiles for. ALWAYS supply one or two UUIDs at a time! Expect really large responses which will overload your context. |

### inventory__get_host_tags

Get tags for specific hosts.

```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool inventory__get_host_tags --host-ids <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--host-ids` | string | yes | Comma-separated list of host IDs (UUIDs) to get tags for. |

### inventory__find_host_by_name

Find a host by its hostname/display name.

```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool inventory__find_host_by_name --hostname <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--hostname` | string | yes | The hostname or display name to search for. |

### content-sources__list_repositories

List repositories with filtering and pagination options.

        🟢 CALL IMMEDIATELY - No information gathering required.


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool content-sources__list_repositories --enabled <value> --limit <value> --offset <value> --name <value> --url <value> --content-type <value> --origin <value> --arch <value> --version <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--enabled` | string | no | Filter by enabled status (True/False). (JSON string) |
| `--limit` | integer | no | Maximum number of repositories to return (default: 10). |
| `--offset` | integer | no | Number of repositories to skip for pagination (default: 0). |
| `--name` | string | no | Filter by repository name (case-insensitive). |
| `--url` | string | no | Filter by repository URL (case-insensitive). |
| `--content-type` | string | no | Filter by content type (e.g., 'rpm', 'ostree'). |
| `--origin` | string | no | Filter by origin (e.g., 'red_hat', 'external'). |
| `--arch` | string | no | Filter by architecture (e.g., 'x86_64', 'aarch64'). |
| `--version` | string | no | Filter by version (e.g., '8', '9'). |

### rbac__get_all_access

Get access information for all Red Hat insights applications.

This endpoint returns access information across all Red Hat insights applications.
The API returns gzipped responses for this endpoint, which are handled by the client.
Use this when you need to see access permissions across all applications.

```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool rbac__get_all_access --username <value> --limit <value> --offset <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--username` | string | no | Optional username to filter access for specific user. |
| `--limit` | integer | no | Maximum number of access records to return (default: 20). |
| `--offset` | integer | no | Number of access records to skip for pagination (default: 0). |

### planning__get_upcoming_changes

List upcoming package changes, deprecations, additions and enhancements.

        🟢 CALL IMMEDIATELY - No information gathering required.

        Use this tool to answer questions about upcoming package changes, deprecations,
        additions, or enhancements in the roadmap when a full list of upcoming items
        is acceptable. When the user asks about a specific RHEL version (for example,
        "What is coming in RHEL 9.4?"), call this tool without parameters and then
        filter and summarize the entries relevant to that version in your response.

        Returns:
            dict: A response object containing:
                    - meta: Metadata including 'count' and 'total'.
                    - data: A list of package records. Each record contains:
                        - name (str): The package name.
                        - type (str): The change type (e.g., 'addition').
                        - release (str): The target release version.
                        - details (dict): Detailed info including 'summary' and 'dateAdded'.


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool planning__get_upcoming_changes
```

### planning__get_appstreams_lifecycle

Get Application Streams lifecycle information.

        🟢 CALL IMMEDIATELY - No information gathering required.

        Use this tool when the user asks about Application Streams lifecycle
        (modules or packages) or wants to understand what streams exist for
        specific RHEL versions.

        Guidance:
        - For detailed lifecycle of modules/packages on a specific RHEL major,
          use mode="raw" and set 'major'.
        - For an overview across RHEL generations (e.g. "what nginx streams
          exist in 8/9/10"), use mode="streams".
        - When the user mentions a human-friendly stream name like ".NET 7",
          use 'application_stream_name'.
        - When the user mentions the technical module/package name, use 'name'.
        - Only use 'kind' when the user explicitly distinguishes between module
          and package implementations.

        Returns:
            str: A JSON-encoded response object containing:
                 - meta: Metadata including:
                     - count (int): Number of records returned in this page.
                     - total (int): Total number of matching records.
                 - data: A list of Application Stream lifecycle records. Each
                   record typically contains:
                     - name (str): Technical package or module name
                       (e.g. 'aspnetcore-runtime-8.0').
                     - display_name (str): Human-friendly display name
                       (e.g. '.NET 8').
                     - application_stream_name (str): Application Stream name
                       (e.g. '.NET 8', 'PostgreSQL 16', 'container-tools').
                     - application_stream_type (str | null): Stream type
                       label (e.g. 'Application Stream',
                       'Full Life Application Stream',
                       'Rolling Application Stream').
                     - stream (str): Stream identifier or version
                       (e.g. '8.0.13', '1.24', '1.14.0').
                     - start_date (str | null): Planned start date for the
                       stream, in ISO format (YYYY-MM-DD).
                     - end_date (str | null): Planned end-of-life date for
                       the stream, in ISO format (YYYY-MM-DD).
                     - impl (str): Implementation kind
                       (e.g. 'package' or 'dnf_module').
                     - initial_product_version (str | null): First RHEL
                       product version where this stream is available
                       (e.g. '9.4', '10.0').
                     - support_status (str): Calculated support status
                       (e.g. 'Supported', 'Near retirement', 'Retired').
                     - os_major (int | null): RHEL major version
                       (e.g. 8, 9, 10).
                     - os_minor (int | null): RHEL minor version
                       where the stream first appears (e.g. 0, 4).
                     - lifecycle (dict | null): Reserved for additional
                       lifecycle metadata (may be null).
                     - rolling (bool): Indicates whether this is a rolling
                       Application Stream (True) or a fixed-lifecycle stream
                       (False).



```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool planning__get_appstreams_lifecycle --mode <value> --major <value> --name <value> --application-stream-name <value> --application-stream-type <value> --kind <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--mode` | string | no | Mode for Application Streams lifecycle: 'raw' (per-major) or 'streams' (cross-major overview). |
| `--major` | string | no | RHEL major version (e.g. '8', '9', '10'). Required when mode='raw'. |
| `--name` | string | no | Module or package technical name filter (e.g. 'aspnetcore-runtime-7.0', 'postgresql'). |
| `--application-stream-name` | string | no | Human-friendly stream name (e.g. '.NET 7', 'PostgreSQL 16', '1.24'). |
| `--application-stream-type` | string | no | Application stream type (e.g. "module" or "package"). |
| `--kind` | string | no | Backend kind filter, e.g. "dnf_module" or "package". |

### planning__get_rhel_lifecycle

Returns life cycle dates for all RHEL majors and minors.

        🟢 CALL IMMEDIATELY - No information gathering required.

        Use this tool when the user asks for RHEL versions and lifecycle timelines, including major versions,
        minor versions, or extended support types (EUS/E4S/ELS).

        For "major-only" versions and timelines (for example, "RHEL 8 lifecycle overview"), call this tool and then
        focus on rows where minor is null. Filtering is performed by you, not the MCP tool.

        For a specific minor (for example, "RHEL 9.2 EUS lifecycle"), call this tool and then
        focus on entries matching the requested major and minor. Interpretation of date windows or version
        selection is done by you.

        When the user mentions dates or "expiring within N days", call this tool and interpret
        the start_date / end_date values to identify relevant versions. Interpretation of date windows or version
        selection is done by you.

        Returns:
            dict: A response object containing:
                    - data: A list of RHEL lifecycle records
                        - name (str): System name
                        - start_date (str): Start date of support
                        - end_date (str): End date of standard support
                        - support_status (str): Status of support, e.g. retired, upcoming_release, supported
                        - display_name (str): How the system should be presented to the customer
                        - major (int): Major system version
                        - minor (int): Minor system version
                        - end_date_e4s (str | null): End date of Update Services for SAP Solutions support
                        - end_date_els (str | null): End date of Extended Life-cycle Support
                        - end_date_eus (str | null): End date of Extended Update Support


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool planning__get_rhel_lifecycle
```

### planning__get_relevant_upcoming

List relevant upcoming package changes, deprecations, additions and enhancements to user's systems.

        🟢 CALL IMMEDIATELY - No information gathering required.

        Use this tool to answer questions about upcoming package changes, deprecations,
        additions, or enhancements in the roadmap filtered by relevance to the user's systems.
        Also to plan for future upgrades and mitigate risk.
        Use this tool over get_upcoming_changes when the user asks about upcoming changes for their systems.

        Returns:
            dict: A response object containing:
                    - meta: Metadata including 'count' and 'total'. A count of 0 means
                            no packages matches for the user's systems.
                    - data: A list of package records. Each record contains:
                        - name (str): The package name.
                        - type (str): The change type (e.g., 'addition').
                        - release (str): The target release version.
                        - details (dict): Detailed info including 'summary' and 'dateAdded'.
                        - potentiallyAffectedSystemsDetail (list): Systems that might be
                          affected by this change, including system IDs, display names,
                          and OS versions.


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool planning__get_relevant_upcoming --major <value> --minor <value>
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--major` | string | no | Restricts relevance evaluation to systems running this RHEL major version. |
| `--minor` | string | no | Used together with major to further restrict relevance evaluation to a specific minor version. Requires major to be specified. |

### planning__get_relevant_appstreams

Get Application Streams relevant to the requester's inventory (includes lifecycle/support dates).

        🟢 CALL IMMEDIATELY - No information gathering required.

        Use this tool when the user asks about Application Streams in their environment
        (inventory, hosts, systems...), such as:
        "Which app streams are we running on RHEL 9?"
        "What successor app streams could we move to from our current streams?"

        Use this tool over get_appstreams_lifecycle when the user asks about their
        inventory, hosts, systems...

        If the question is scoped to a specific RHEL major or minor, set major
        (and optionally minor) so that relevance is computed only from systems on
        that version.

        If the user wants only streams currently running (what is installed/in use
        in inventory), set include_related=false.
        If the user asks whether newer versions exist, wants upgrade recommendations,
        or wants successor streams to consider, set include_related=true and review
        entries where related=true as potential candidates.

        If the user needs an exhaustive catalog view of all streams available for a
        given component (e.g., "list all Node.js streams across RHEL 8/9/10"), use
        get_appstreams_lifecycle.

        The backend computes relevance based on actual host data in the user's inventory. This tool
        does not perform any client-side filtering; all evaluation is performed by the backend.

        Returns:
            str: A JSON-encoded response object containing:
                 - meta: Metadata including:
                     - count (int): Number of records returned.
                     - total (int): Total number of matching records.
                 - data: A list of Application Stream records relevant to the user's inventory.
                   Each record contains:
                     - name (str): Technical package or module name.
                     - display_name (str): Human-friendly display name.
                     - application_stream_name (str): Application Stream name.
                     - stream (str): Stream identifier or version.
                     - start_date (str | null): Planned start date (ISO format).
                     - end_date (str | null): Planned end-of-life date (ISO format).
                     - support_status (str): Support status (e.g. 'Supported', 'Retired').
                     - os_major (int | null): RHEL major version.
                     - os_minor (int | null): RHEL minor version.
                     - related (bool): Indicates if this is a related/successor stream (true)
                       or currently in use (false).


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool planning__get_relevant_appstreams --major <value> --minor <value> --include-related
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--major` | string | no | Restricts relevance evaluation to systems running this RHEL major version. |
| `--minor` | string | no | Used together with major to further restrict relevance evaluation to a specific minor version. Requires major to be specified. |
| `--include-related` | boolean | no | If true, returns streams currently used plus related/successor streams. If false, returns only streams currently used in inventory. |

### planning__get_relevant_rhel_lifecycle

Returns RHEL lifecycle information for systems in the requester's inventory.

        🟢 CALL IMMEDIATELY - No information gathering required.

        Use this tool when the user asks about RHEL lifecycle in their own environment, for example:
        - Which RHEL versions are we currently running, and when do they go out of support?
        - What future RHEL 8 minor versions could we upgrade to that are still supported?

        When the question is scoped to a specific RHEL major (or major/minor), set major (and optionally minor)
        so relevance is calculated only from systems on that version.

        If the user wants only what is currently running, set include_related=False
        (default, not needed to be specified).

        If the user wants upgrade options or newer streams related to what they run today, set include_related=True and
        look at items where related=true as potential targets.

        Response guidance:
        - Summarize support status and end dates in plain language.
        - If a version is retired or near end-of-support, call out the impact (loss of updates, risk).
        - Provide recommended actions (e.g., plan upgrade, evaluate supported minor versions).

        Returns:
            str: A JSON-encoded response object containing:
                 - meta: Metadata including:
                     - count (int): Number of records returned.
                     - total (int): Total number of matching records.
                 - data: A list of RHEL lifecycle records relevant to the user's inventory.
                   Each record contains:
                     - name (str): RHEL version name.
                     - display_name (str): Human-friendly display name.
                     - os_major (int | null): RHEL major version.
                     - os_minor (int | null): RHEL minor version.
                     - start_date (str | null): Planned start date (ISO format).
                     - end_date (str | null): Planned end-of-life date (ISO format).
                     - support_status (str): Support status (e.g. 'Supported', 'Retired').
                     - count (int): Number of systems running this RHEL version.
                     - lifecycle_type (str): Type of RHEL version (e.g. 'mainline', 'extended update support (EUS)',
                     'extended life-cycle support (ELS)', 'update services for SAP solutions (E4S)').
                     - related (bool): True when include_related=true and the version
                     is a suggested upgrade target.


```bash
uv run --with fastmcp python insights-mcp-cli.py call-tool planning__get_relevant_rhel_lifecycle --major <value> --minor <value> --include-related
```

| Flag | Type | Required | Description |
|------|------|----------|-------------|
| `--major` | string | no | Restricts relevance evaluation to systems running this RHEL major version. |
| `--minor` | string | no | Used together with major to further restrict relevance evaluation to a specific minor version. Requires major to be specified. |
| `--include-related` | boolean | no | When true, returns both RHEL versions observed in inventory and additional higher-minor or future versions of the same major that are still supported but not yet deployed (marked as related=true). When false, returns only RHEL versions actually observed in the requester's inventory. |

## Utility Commands

```bash
uv run --with fastmcp python insights-mcp-cli.py list-tools
uv run --with fastmcp python insights-mcp-cli.py list-resources
uv run --with fastmcp python insights-mcp-cli.py read-resource <uri>
uv run --with fastmcp python insights-mcp-cli.py list-prompts
uv run --with fastmcp python insights-mcp-cli.py get-prompt <name> [key=value ...]
```
