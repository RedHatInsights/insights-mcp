# Red Hat Insights RBAC MCP Server

Diagnostics for Role-Based Access Control when using other Insights MCP toolsets.

## Tools

| Tool | Purpose |
|------|---------|
| `explain_access_denied` | Primary 403 diagnostic: missing console **role display names** |
| `lookup_tool_requirements` | Required role display names for one MCP tool (no access check) |
| `get_caller_access` | Caller permissions for one application |
| `get_caller_access_all` | All caller permissions (paginated) |

## Principal semantics

`get_caller_access*` and `explain_access_denied` use the **same credentials as other MCP
toolsets** (service account env vars, headers, or Bearer token). That is usually the **MCP
service account**, not the human using the chat UI.

To inspect another user’s permissions, pass `username=` only if your caller has RBAC
admin rights to query principals.

## Docs regeneration

```bash
make generate-docs
```

Rewrites generated RBAC role names in README and getting-started skills from
rbac-config plus `configs/tool_rest_map.json`.

## API

Base path: `/api/rbac/v1`.
