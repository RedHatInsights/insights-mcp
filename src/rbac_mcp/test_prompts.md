# RBAC MCP Test Prompts

Test prompts for the Red Hat Insights RBAC (Role-Based Access Control) MCP server.

Currently, only the `get_all_access` function is implemented.

## Access Queries

### Get Access Across All Applications
```
Show me access permissions across all applications
```

### Get Access for a Specific User
```
Show me access permissions for user "john.doe" across all applications
```

### Get Access with Pagination
```
Get the first 50 access records across all applications
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

### User Access Review
```
Review access permissions for user "jane.smith" across all Red Hat applications to ensure they have appropriate access.
```
