# RBAC MCP Test Prompts

Test prompts for the Red Hat Insights RBAC (Role-Based Access Control) MCP server.

Tools: `explain_access_denied`, `lookup_tool_requirements`, `get_caller_access`,
`get_caller_access_all`.

## Access Queries

### Get Access Across All Applications
```
please check my insights permissions are there any missing for insights-mcp?
```

### Get Access for a Specific User
```
Show me access permissions for user "john.doe" across all applications
```

### Get Access for One Application
```
Show my RBAC permissions for the vulnerability application
```

### Get Access for Service Account
```
What access permissions does service account "automation-bot" have across all Red Hat applications?
```

## Troubleshooting Scenarios

### Permission Debugging
```
I can't access certain features in Red Hat services. Show me all my access permissions across all applications to help debug the issue.
```

### Diagnose a 403
```
vulnerability__get_system_cves returned 403. Explain why I don't have access.
```

### User Access Review
```
Review access permissions for user "jane.smith" across all Red Hat applications to ensure they have appropriate access.
```
