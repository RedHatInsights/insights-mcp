# Insights MCP

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server to interact with insights services like the
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

1. Go to https://console.redhat.com → Click Settings (Gear Icon) →  "Service Accounts"
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
2. **Navigate to User Access Settings**: Click Settings (Gear Icon) → "User Access" → "Groups"
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
Try this one-click installation or follow the instructions below.

[![Install with Podman in VS Code](https://img.shields.io/badge/VS_Code-Install_Insights_MCP-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=insights-mcp&config=%7B%22type%22%3A%20%22stdio%22%2C%20%22command%22%3A%20%22podman%22%2C%20%22args%22%3A%20%5B%22run%22%2C%20%22--env%22%2C%20%22INSIGHTS_CLIENT_ID%22%2C%20%22--env%22%2C%20%22INSIGHTS_CLIENT_SECRET%22%2C%20%22--interactive%22%2C%20%22--rm%22%2C%20%22quay.io%2Fredhat-services-prod%2Finsights-management-tenant%2Finsights-mcp%2Finsights-mcp%3Alatest%22%5D%2C%20%22env%22%3A%20%7B%22INSIGHTS_CLIENT_ID%22%3A%20%22%24%7Binput%3Ainsights_client_id%7D%22%2C%20%22INSIGHTS_CLIENT_SECRET%22%3A%20%22%24%7Binput%3Ainsights_client_secret%7D%22%7D%7D&inputs=%5B%7B%22id%22%3A%20%22insights_client_id%22%2C%20%22type%22%3A%20%22promptString%22%2C%20%22description%22%3A%20%22Enter%20the%20Red%20Hat%20Insights%20Client%20ID%22%2C%20%22default%22%3A%20%22%22%2C%20%22password%22%3A%20true%7D%2C%20%7B%22id%22%3A%20%22insights_client_secret%22%2C%20%22type%22%3A%20%22promptString%22%2C%20%22description%22%3A%20%22Enter%20the%20Red%20Hat%20Insights%20Client%20Secret%22%2C%20%22default%22%3A%20%22%22%2C%20%22password%22%3A%20true%7D%5D)<br>
(Note: this uses the `quay.io` container image)

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

Try this one-click installation or follow the instructions below.

[![Install with Podman in Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=insights-mcp&config=eyJ0eXBlIjoic3RkaW8iLCJjb21tYW5kIjoicG9kbWFuIHJ1biAtLWVudiBJTlNJR0hUU19DTElFTlRfSUQgLS1lbnYgSU5TSUdIVFNfQ0xJRU5UX1NFQ1JFVCAtLWludGVyYWN0aXZlIC0tcm0gcXVheS5pby9yZWRoYXQtc2VydmljZXMtcHJvZC9pbnNpZ2h0cy1tYW5hZ2VtZW50LXRlbmFudC9pbnNpZ2h0cy1tY3AvaW5zaWdodHMtbWNwOmxhdGVzdCIsImVudiI6eyJJTlNJR0hUU19DTElFTlRfSUQiOiIiLCJJTlNJR0hUU19DTElFTlRfU0VDUkVUIjoiIn19)<br>
(Note: this uses the `quay.io` container image)

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

#### Claude Code

For instance, to use Claude Code with the STDIO server, use this command:

```bash
claude mcp add insights-mcp -- podman run --env INSIGHTS_CLIENT_ID --env INSIGHTS_CLIENT_SECRET --interactive --rm ghcr.io/redhatinsights/insights-mcp:latest
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

## Releases
There are two container images published for this MCP server.

 * `ghcr.io/redhatinsights/insights-mcp:latest`
 * `quay.io/redhat-services-prod/insights-management-tenant/insights-mcp/insights-mcp:latest`

They are both based on `main` branch and you can use either of them.

## Disclaimer

This software is provided "as is" without warranty of any kind, either express or implied. Use at your own risk. The authors and contributors are not liable for any damages or issues that may arise from using this software.

## Contributing
Please refer to the [hacking guide](HACKING.md) to learn more.
