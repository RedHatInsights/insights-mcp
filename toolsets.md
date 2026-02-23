# All available toolsets

Tools marked as read-write **`(rw)`** are excluded by default. Use the `--all-tools` flag when starting the server to include them.

## image-builder
- `get_blueprint_details`: Get blueprint details.
- `get_blueprints`: Show user's image blueprints (saved image templates/configurations for
- `get_compose_details`: Get detailed information about a specific image build.
- `get_composes`: Get a list of all image builds (composes) with their UUIDs and basic status.
- `get_distributions`: Get the list of distributions available to build images with.
- `get_openapi`: Get OpenAPI spec. Use this to get details e.g for a new blueprint
- `get_org_id`: Get the organization ID for RHEL image registration/subscription.
- `blueprint_compose` **`(rw)`**: Compose an image from a blueprint UUID created with create_blueprint, get_blueprints.
- `create_blueprint` **`(rw)`**: Create a custom Linux image blueprint.
- `update_blueprint` **`(rw)`**: Update a blueprint.

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
- `list_hosts`: List hosts with filtering and sorting options.

## content-sources
- `list_repositories`: List repositories with filtering and pagination options.

## rbac
- `get_all_access`: Get access information for all Red Hat insights applications.

## planning
- `get_appstreams_lifecycle`: Get Application Streams lifecycle information.
- `get_relevant_upcoming`: List relevant upcoming package changes, deprecations, additions and enhancements to user's…
- `get_rhel_lifecycle`: Returns life cycle dates for all RHEL majors and minors.
- `get_upcoming_changes`: List upcoming package changes, deprecations, additions and enhancements.
