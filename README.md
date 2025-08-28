# Insights MCP

This repo is in a DRAFT and playground state!

An MCP server to interact with insights services like the
 * [advisor](https://docs.redhat.com/en/documentation/red_hat_insights/1-latest/html/assessing_rhel_configuration_issues_using_the_red_hat_insights_advisor_service/index)
 * [hosted image builder](https://osbuild.org/docs/hosted/architecture/)
 * [inventory](https://docs.redhat.com/en/documentation/red_hat_insights/1-latest/html/viewing_and_managing_system_inventory/index)
 * [remediations](https://docs.redhat.com/en/documentation/red_hat_insights/1-latest/html/red_hat_insights_remediations_guide/index)
 * [vulnerability](https://docs.redhat.com/en/documentation/red_hat_insights/1-latest/html/assessing_and_monitoring_security_vulnerabilities_on_rhel_systems/index)

## Toolsets

See [toolsets.md](toolsets.md) for the toolsets available in the MCP server.

## Authentication

**Note**: Authentication is only required for accessing Red Hat Insights APIs. The MCP server itself does not require authentication.

### Service Account Setup

1. Go to https://console.redhat.com → `'YOUR USER' ➡ My User Access ➡ Service Accounts`
2. Create a service account and set environment variables `INSIGHTS_CLIENT_ID` and `INSIGHTS_CLIENT_SECRET`

### Required Permissions by Toolset

Different toolsets require specific roles for your service account:

- **Advisor tools**: `RHEL Advisor viewer`
- **Inventory tools**: `Inventory Hosts viewer`
- **Vulnerability tools**: `Vulnerability viewer`, `Inventory Hosts viewer`
- **Remediation tools**: `Remediations user`

### Granting Permissions to Service Accounts

By default, service accounts have no access. An organization administrator must assign permissions:

For detailed step-by-step instructions, see this video tutorial: [Service Account Permissions Setup](https://www.youtube.com/watch?v=UvNcmJsbg1w)

1. **Log in as Organization Administrator** with User Access administrator role
2. **Navigate to User Access Settings**: Click gear icon → "User Access" → "Groups"
3. **Assign permissions** (choose one option):

   **Option A - Create New Group:**
   - Create new group (e.g., `mcp-service-accounts`)
   - Add required roles (e.g., RHEL Advisor viewer, Inventory Hosts viewer, etc.)
   - Add your service account to this group

   **Option B - Use Existing Group:**
   - Open existing group with necessary roles
   - Go to "Service accounts" tab
   - Add your service account to the group

Your service account will inherit all roles from the assigned group.

### ⚠️ Security Remarks ⚠️

If you start this MCP server locally (with `podman` or `docker`) make sure the container is not exposed to the internet. In this scenario it's probably fine to use `INSIGHTS_CLIENT_ID` and `INSIGHTS_CLIENT_SECRET` although your MCP Client (e.g. VSCode, Cursor, etc.) can get your `INSIGHTS_CLIENT_ID` and `INSIGHTS_CLIENT_SECRET`.

For a deployment where you connect to this MCP server from a different machine, you should consider that `INSIGHTS_CLIENT_ID` and `INSIGHTS_CLIENT_SECRET` are transferred to the MCP server and you are trusting the remote MCP server not to leak them.

In both cases if you are in doubt, please disable/remove the `INSIGHTS_CLIENT_ID` and `INSIGHTS_CLIENT_SECRET` from your account after you are done using the MCP server.

## Integrations

### VSCode
For the usage in your project, create a file called `.vscode/mcp.json` with
the following content.

```
{
    "inputs": [
        {
            "id": "insights_client_id",
            "type": "promptString",
            "description": "Enter the Red Hat Insights Client ID",
            "default": "",
            "password": true
        },
        {
            "id": "insights_client_secret",
            "type": "promptString",
            "description": "Enter the Red Hat Insights Client Secret",
            "default": "",
            "password": true
        }
    ],
    "servers": {
        "insights-mcp-stdio": {
            "type": "stdio",
            "command": "podman",
            "args": [
                "run",
                "--env",
                "INSIGHTS_CLIENT_ID",
                "--env",
                "INSIGHTS_CLIENT_SECRET",
                "--interactive",
                "--rm",
                "ghcr.io/redhatinsights/insights-mcp:latest"
            ],
            "env": {
                "INSIGHTS_CLIENT_ID": "${input:insights_client_id}",
                "INSIGHTS_CLIENT_SECRET": "${input:insights_client_secret}"
            }
        }
    }
}
```

### Cursor

Cursor doesn't seem to support `inputs` you need to add your credentials in the config file.
To start the integration create a file `~/.cursor/mcp.json` with
```
{
  "mcpServers": {
    "insights-mcp": {
        "type": "stdio",
        "command": "podman",
        "args": [
            "run",
            "--env",
            "INSIGHTS_CLIENT_ID",
            "--env",
            "INSIGHTS_CLIENT_SECRET",
            "--interactive",
            "--rm",
            "ghcr.io/redhatinsights/insights-mcp:latest"
        ],
        "env": {
            "INSIGHTS_CLIENT_ID": "",
            "INSIGHTS_CLIENT_SECRET": ""
        }
    }
  }
}
```

or use it via "Streamable HTTP"

start the server:

```
podman run --net host --rm ghcr.io/redhatinsights/insights-mcp:latest http
```

then integrate:

```
{
    "mcpServers": {
        "insights-mcp-http": {
            "type": "http",
            "url": "http://localhost:8000/mcp",
            "headers": {
                "insights-client-id": "",
                "insights-client-secret": ""
            }
        }
    }
}
```

### Claude Desktop

For Claude Desktop there is an extension file in the [release section](https://github.com/RedHatInsights/insights-mcp/releases) of the project.

Just download the `insights-mcp*.dxt` file and add this in Claude Desktop with

`Settings -> Extensions -> Advanced Extensions Settings -> Install Extension…`

### Generic STDIO

For generic integration into other tools via STDIO, you should set the environment variables
`INSIGHTS_CLIENT_ID` and `INSIGHTS_CLIENT_SECRET` and use this command for an
integration using podman:

```bash
podman run --env INSIGHTS_CLIENT_ID --env INSIGHTS_CLIENT_SECRET --interactive --rm ghcr.io/redhatinsights/insights-mcp:latest
```

## Examples

It's probably best to just ask the LLM you just attached to the MCP server to.
e.g.
```
Please explain insights-mcp and what I can do with it?
```

For example questions specific to each toolset please have a look at the test files:

 * [`image-builder-mcp`](src/image_builder_mcp/tests/test_llm_integration_easy.py#L20)
 * [`inventory-mcp`](src/inventory_mcp/test_prompts.md)
 * [`remediations-mcp`](src/remediations_mcp/test_prompts.md)
 * [`advisor-mcp`](src/advisor_mcp/test_prompts.md)
 * [`vulnerability-mcp`](src/vulnerability_mcp/test_prompts.md)

## Contributing
Please refer to the [hacking guide](HACKING.md) to learn more.
