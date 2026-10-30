# OCP Advisor MCP Test Prompts

- Get the deployed ccx-ocp-rules version for OCP Advisor in production.
- Verify the latest OCP Advisor rules release was deployed to production and show the Content Service commit and build metadata.
- Check that the OCP Advisor production backend is healthy across Smart Proxy, Aggregator, and Content Service.
- List the OpenShift clusters visible to OCP Advisor and summarize their recommendation hit counts and risk levels.
- Show me the Insights Advisor recommendations for OpenShift cluster 11111111-2222-3333-4444-555555555555, including the risk level and what I should do about each finding.
- Include disabled recommendations when listing the findings for OpenShift cluster 11111111-2222-3333-4444-555555555555.
- Which namespaces have DVO workload recommendations and how severe are they?
- Show the DVO recommendations for namespace aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee of cluster 11111111-2222-3333-4444-555555555555, including the affected workloads.
- For clusters 11111111-2222-3333-4444-555555555555 and 22222222-3333-4444-5555-666666666666, get the upgrade-risk predictions and explain any alerts or operator conditions that would block an upgrade.
