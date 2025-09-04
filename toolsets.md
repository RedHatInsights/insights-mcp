# All available toolsets

## image-builder
- `get_openapi`: Get OpenAPI spec. Use this to get details e.g for a new blueprint
- `create_blueprint`: Create a custom Linux image blueprint.
- `update_blueprint`: Update a blueprint.
- `get_blueprints`: Show user's image blueprints (saved image templates/configurations for
- `get_blueprint_details`: Get blueprint details.
- `get_composes`: Get a list of all image builds (composes) with their UUIDs and basic status.
- `get_compose_details`: Get detailed information about a specific image build.
- `blueprint_compose`: Compose an image from a blueprint UUID created with create_blueprint, get_bl…
- `get_distributions`: Get the list of distributions available to build images with.

## vulnerability
- `get_openapi`: Get Red Hat Insights Vulnerability OpenAPI specification in JSON format.
- `get_cves`: Get list of CVEs affecting the account.
- `get_cve`: Get details about specific CVE.
- `get_cve_systems`: Get list of systems affected by a given CVE.
- `get_system_cves`: Get list of CVEs affecting a given system.
- `get_systems`: Get list of systems in Insights Vulnerability inventory.
- `explain_cves`: Explain why CVEs are affecting my environment.

## remediations
- `create_vulnerability_playbook`: Create remediation playbook for given CVEs on given systems to m…

## advisor
- `get_active_rules`: Get Active Advisor Recommendations for Account
- `get_rule_from_node_id`: Find Advisor Recommendations by Knowledge Base Solutions or Articles by ID
- `get_rule_details`: Get Detailed Advisor Recommendation Information
- `get_hosts_hitting_a_rule`: Get Systems Affected by Advisor Recommendation
- `get_hosts_details_hitting_a_rule`: Get Detailed System Information for Advisor Recommendation
- `get_rule_by_text_search`: Find Advisor Recommendations by Text Search
- `get_recommendations_statistics`: Get Statistics of Recommendations Across Categories and Risks

## inventory
- `list_hosts`: List hosts with filtering and sorting options.
- `get_host_details`: Get detailed information for specific hosts by their IDs.
- `get_host_system_profile`: Get detailed system profile information for specific hosts.
- `get_host_tags`: Get tags for specific hosts.
- `find_host_by_name`: Find a host by its hostname/display name.

## content-sources
- `list_repositories`: List repositories with filtering and pagination options.

## rbac
- `get_all_access`: Get access information for all applications.
