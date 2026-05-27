# Red Hat Insights RBAC MCP Server

Diagnostics for Role-Based Access Control when using other Insights MCP toolsets.

## Tools

| Tool | Purpose |
|------|---------|
| `explain_access_denied` | Primary 403 diagnostic: required permissions (manifest) vs caller (live RBAC API) |
| `lookup_tool_requirements` | Requirements only for one MCP tool (no API call) |
| `get_caller_access` | Caller permissions for one application |
| `get_caller_access_all` | All caller permissions (paginated) |
| `get_all_access` | **Deprecated** — use `get_caller_access_all` |

## Principal semantics

`get_caller_access*` and `explain_access_denied` use the **same credentials as other MCP
toolsets** (service account env vars, headers, or Bearer token). That is usually the **MCP
service account**, not the human using the chat UI.

To inspect another user’s permissions, pass `username=` only if your caller has RBAC
admin rights to query principals.

## Manifest regeneration

```bash
make generate-rbac-manifest
```

Updates `src/insights_mcp/rbac/data/tool_rbac_manifest.json` and
`role_recommendations.json`.

## API

Base path: `/api/rbac/v1` (see [apis/rbac-openapi.json](../../apis/rbac-openapi.json)).
