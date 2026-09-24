# All available toolsets

Tools marked as read-write **`(rw)`** are excluded by default. Use the `--all-tools` flag when starting the server to include them.

## image-builder
- `get_blueprint_details`: 🟢 Blueprint details by UUID, name, or reply_id from get_blueprints.
- `get_blueprints`: 🟢 List blueprints. Use limit/offset from the user. Paging hints in response footer.
- `get_compose_details`: 🟢 One compose/image build status & details. UUID from get_composes—not "latest" alone.
- `get_composes`: 🟢 List image builds (composes) with status; newest first. limit/offset default 7, 0.
- `get_distributions`: 🟢 List RHEL distributions (latest minor per major). No Fedora/CentOS Stream support.
- `get_openapi`: 🟢 OpenAPI spec. Optional endpoints=GET:/blueprints,POST:/blueprints to shrink payload.
- `get_org_id`: 🟢 RHEL org ID for blueprint registration. Never invent org IDs.
- `blueprint_compose` **`(rw)`**: 🟡 Start compose for a blueprint UUID. Confirm UUID via get_blueprints first.
- `create_blueprint` **`(rw)`**: 🔴 Create blueprint: gather name, distro, arch, image type; use get_openapi…
- `update_blueprint` **`(rw)`**: 🟡 Update blueprint. Confirm UUID; schema via get_openapi PUT:/blueprints/{id}.

## rhsm
- `get_activation_key`: Get a specific activation key by name.
- `get_activation_keys`: Get the list of activation keys available to the authenticated user.

## vulnerability
- `explain_cves`: Explain why CVEs are affecting my environment.
- `get_cve`: Get details about specific CVE.
- `get_cve_systems`: Get list of systems affected by a given CVE.
- `get_cves`: Get list of CVEs affecting the account.
- `get_openapi`: Get $container_brand_long Vulnerability OpenAPI specification in JSON format.
- `get_system_cves`: Get list of CVEs affecting a given system.
- `get_systems`: Get list of systems in $container_brand_long Vulnerability inventory.
- `load_cve_dashboard`: Show, list, or display CVEs — account-level or for a specific system — in an interactive…

## remediations
- `create_vuln_playbook` **`(rw)`**: Create remediation playbook for given CVEs on given systems to mitigate…

## advisor
- `get_active_rules`: Get Active Advisor Recommendations for Account
- `get_hosts_details_for_rule`: Get Detailed System Information for Advisor Recommendation
- `get_hosts_hitting_a_rule`: Get Systems Affected by Advisor Recommendation
- `get_recommendations_stats`: Get Statistics of Recommendations Across Categories and Risks
- `get_rule_by_text_search`: Find Advisor Recommendations by Text Search
- `get_rule_details`: Get Detailed Advisor Recommendation Information
- `get_rule_from_node_id`: Find Advisor Recommendations using Knowledge Base solution ID or article ID

## inventory
- `find_host_by_name`: Find a host by its hostname/display name.
- `get_host_details`: Get detailed information for specific hosts by their IDs.
- `get_host_system_profile`: Get detailed system profile information for specific hosts.
- `get_host_tags`: Get tags for specific hosts.
- `get_workspace`: Get details for one or more workspaces by ID.
- `list_hosts`: List hosts with filtering and sorting options.
- `list_workspace_hosts`: List hosts that belong to a workspace.
- `list_workspaces`: List Inventory workspaces (console UI name for Inventory groups).
- `load_inventory_dashboard`: Show, list, or display fleet inventory in an interactive dashboard.

## content-sources
- `list_repositories`: List repositories with filtering and pagination options.

## rbac
- `explain_access_denied`: Diagnose a 403 access denial for a specific MCP tool call.
- `get_caller_access`: Get RBAC access for the authenticated caller for one application.
- `get_caller_access_all`: List all RBAC permissions for the authenticated MCP caller (paginated fetch).
- `lookup_tool_requirements`: Return the console role names required for an MCP tool.

## planning
- `get_appstreams_lifecycle`: Get Application Streams lifecycle information.
- `get_relevant_appstreams`: Get Application Streams relevant to the requester's inventory (includes lifecycle/support…
- `get_relevant_rhel_lifecycle`: Returns RHEL lifecycle information for systems in the requester's inventory.
- `get_relevant_upcoming`: List relevant upcoming package changes, deprecations, additions and enhancements to user's…
- `get_rhel_lifecycle`: Returns life cycle dates for all RHEL majors and minors.
- `get_upcoming_changes`: List upcoming package changes, deprecations, additions and enhancements.
