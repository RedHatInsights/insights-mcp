# Red Hat Insights RBAC MCP Server

This MCP server provides tools to interact with Red Hat Insights Role-Based Access Control (RBAC) API. Currently, it implements a single tool to check access permissions across all applications.

## Features

- **Access Management**: Get access information across all applications for users and service accounts

## Available Tools

Currently, only one tool is implemented:

### Access Tools
- `get_all_access`: Get access information across all applications (handles gzipped responses)

## Planned Tools (Not Yet Implemented)

The following tools are planned for future implementation:

### Access Tools
- `get_access`: Get access information for a specific application
- `get_applications`: Get list of available applications
- `get_application_permissions`: Get available permissions for a specific application

### Role Management Tools
- `get_roles`: Get list of roles with filtering and pagination
- `get_role_details`: Get detailed information about a specific role

### Permission Policy Tools
- `get_permission_policies`: Get list of permission policies
- `get_policy_details`: Get detailed information about a specific permission policy

### Group Management Tools
- `get_groups`: Get list of groups
- `get_group_details`: Get detailed information about a specific group

### Principal Management Tools
- `get_principals`: Get list of principals (users/service accounts)

## API Endpoint

The server connects to the Red Hat Insights RBAC API at:
```
https://console.redhat.com/api/rbac/v1/
```

## Authentication

This server uses the same authentication mechanism as other Insights MCP servers:
- OAuth2 with Red Hat SSO
- Service Account credentials
- Standard Insights API authentication

## Special Handling

### Gzipped Responses
The RBAC API returns gzipped responses in certain cases, particularly when querying access information across all applications (when the application parameter is empty). The client automatically handles gzip decompression transparently.

- `get_access`: Requires an application parameter to avoid gzipped responses
- `get_all_access`: Specifically designed to handle gzipped responses from the API

## Required Permissions

To use this server, your Service Account needs appropriate RBAC permissions:
- **RBAC Administrator**: For full access to all RBAC operations
- **RBAC Viewer**: For read-only access to RBAC information

## Usage Examples

### Get access information across all applications
```
Show me all access permissions for my account across all applications
```

### Get access for a specific user
```
What access permissions does user 'john.doe' have across all applications?
```

## API Reference

This server implements the Red Hat Developer Hub RBAC REST API as documented at:
https://docs.redhat.com/en/documentation/red_hat_developer_hub/1.2/html/authorization/con-rbac-rest-api_title-authorization

Currently implemented endpoints:
- `/access/` - Access information for applications (with empty application parameter to get all applications)

Planned endpoints for future implementation:
- `/access/` - Access information for specific applications
- `/roles/` - Role management
- `/policies/` - Permission policies
- `/groups/` - Group management
- `/principals/` - Principal (user/service account) management
- `/applications/` - Application information
