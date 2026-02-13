# Red Hat Lightspeed MCP
_(formerly known as Insights MCP)_

Red Hat Lightspeed Model Context Protocol ([MCP](https://modelcontextprotocol.io)) server is a lightweight, self-hosted solution that connects LLM-based agents - such as Claude Desktop and other MCP-compatible tools - to Red Hat Lightspeed services.

## Features
 * Supports read-only operations: All toolsets can be restricted using the `--read-only` flag or via RBAC permissions.
 * Provides natural language prompts: provides an ability to use natural language for querying Red Hat Lightspeed services

## Supported Lightspeed Services
 * [advisor](https://docs.redhat.com/en/documentation/red_hat_insights/1-latest/html/assessing_rhel_configuration_issues_using_the_red_hat_insights_advisor_service/index)
 * [hosted image builder](https://osbuild.org/docs/hosted/architecture/)
 * [inventory](https://docs.redhat.com/en/documentation/red_hat_insights/1-latest/html/viewing_and_managing_system_inventory/index)
 * [planning](https://docs.redhat.com/en/documentation/red_hat_lightspeed/1-latest/html/dynamically_creating_a_digital_roadmap_to_manage_rhel_systems/index)
 * [remediations](https://docs.redhat.com/en/documentation/red_hat_insights/1-latest/html/red_hat_insights_remediations_guide/index)
 * [vulnerability](https://docs.redhat.com/en/documentation/red_hat_insights/1-latest/html/assessing_and_monitoring_security_vulnerabilities_on_rhel_systems/index)

## Setup and usage

### Authentication

**Note**: Authentication is only required for accessing Red Hat Lightspeed APIs. The MCP server itself does not require authentication.

There are two ways to authenticate:

1. **Service Account** (client_id + client_secret) — create a service account and provide the credentials via environment variables or HTTP headers.
2. **JWT Bearer Token** — provide a pre-existing JWT token via the `Authorization: Bearer <token>` HTTP header (SSE/HTTP transports only).

#### Service Account Setup

1. Go to https://console.redhat.com → Click Settings (⚙️ Gear Icon) →  "Service Accounts"
2. Create a service account and remember `Client ID` and `Client secret` for later.<br>
   See below in the integration instructions, there they are respectively referred to as
   `LIGHTSPEED_CLIENT_ID` and `LIGHTSPEED_CLIENT_SECRET`.

#### Required Permissions by Toolset

Different toolsets require specific roles for your service account:

- **Advisor tools**: `RHEL Advisor viewer`
- **Inventory tools**: `Inventory Hosts viewer`
- **Vulnerability tools**: `Vulnerability viewer`, `Inventory Hosts viewer`
- **Remediation tools**: `Remediations user`

#### Granting Permissions to Service Accounts

By default, service accounts have no access. An organization administrator must assign permissions. The MCP server will only be able to perform tasks that it has permission to perform. For example, if the user wants to allow read-only operations and deny write operations, this can be accomplished via the permissions system.

For detailed step-by-step instructions, see this video tutorial: [Service Account Permissions Setup](https://www.youtube.com/watch?v=UvNcmJsbg1w)

1. **Log in as Organization Administrator** with User Access administrator role
2. **Navigate to User Access Settings**: Click Settings (⚙️ Gear Icon) → "User Access" → "Groups"
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

#### ⚠️ Security Remarks ⚠️

If you start this MCP server locally (with `podman` or `docker`) make sure the container is not exposed to the internet. In this scenario it's probably fine to use `LIGHTSPEED_CLIENT_ID` and `LIGHTSPEED_CLIENT_SECRET` although your MCP Client (e.g. VSCode, Cursor, etc.) can get your `LIGHTSPEED_CLIENT_ID` and `LIGHTSPEED_CLIENT_SECRET`.

For a deployment where you connect to this MCP server from a different machine, you should consider that `LIGHTSPEED_CLIENT_ID` and `LIGHTSPEED_CLIENT_SECRET` (or your JWT Bearer token) are transferred to the MCP server and you are trusting the remote MCP server not to leak them.

In both cases if you are in doubt, please disable/remove the `LIGHTSPEED_CLIENT_ID` and `LIGHTSPEED_CLIENT_SECRET` from your account after you are done using the MCP server.


## Technical Info
### Toolsets

See [toolsets.md](toolsets.md) for the toolsets available in the MCP server.

## Integrations

### Prerequisites

Make sure you have `podman` installed.<br>
(Docker is fine too but the commands below have to be adapted accordingly)

You can install it with `sudo dnf install podman` on Fedora/RHEL/CentOS,
or on macOS use either [Podman Desktop](https://podman-desktop.io/) or `brew install podman`.

⚠️ **Note** if you use Podman on macOS, you sometimes need to set the path to `podman` explicitly.
E.g. replace `podman` with the full path. Should be something like

 * `/usr/local/bin/podman`
 * `/opt/homebrew/bin/podman`
 * …

You can find the path by running `which podman` in your terminal.

### VSCode

First check the [prerequisites](#prerequisites) section.

#### Option 1: One-click installation (easiest)

[![Install with Podman in VS Code](https://img.shields.io/badge/VS_Code-Install_Red_Hat_Lightspeed_MCP-0098FF?style=flat-square&logo=visualstudiocode&logoColor=white)](https://insiders.vscode.dev/redirect/mcp/install?name=red-hat-lightspeed-mcp&config=%7B%22type%22%3A%20%22stdio%22%2C%20%22command%22%3A%20%22podman%22%2C%20%22args%22%3A%20%5B%22run%22%2C%20%22--env%22%2C%20%22LIGHTSPEED_CLIENT_ID%22%2C%20%22--env%22%2C%20%22LIGHTSPEED_CLIENT_SECRET%22%2C%20%22--interactive%22%2C%20%22--rm%22%2C%20%22quay.io%2Fredhat-services-prod%2Finsights-management-tenant%2Finsights-mcp%2Fred-hat-lightspeed-mcp%3Alatest%22%5D%2C%20%22env%22%3A%20%7B%22LIGHTSPEED_CLIENT_ID%22%3A%20%22%24%7Binput%3Alightspeed_client_id%7D%22%2C%20%22LIGHTSPEED_CLIENT_SECRET%22%3A%20%22%24%7Binput%3Alightspeed_client_secret%7D%22%7D%7D&inputs=%5B%7B%22id%22%3A%20%22lightspeed_client_id%22%2C%20%22type%22%3A%20%22promptString%22%2C%20%22description%22%3A%20%22Enter%20the%20Red%20Hat%20Lightspeed%20Client%20ID%22%2C%20%22default%22%3A%20%22%22%2C%20%22password%22%3A%20true%7D%2C%20%7B%22id%22%3A%20%22lightspeed_client_secret%22%2C%20%22type%22%3A%20%22promptString%22%2C%20%22description%22%3A%20%22Enter%20the%20Red%20Hat%20Lightspeed%20Client%20Secret%22%2C%20%22default%22%3A%20%22%22%2C%20%22password%22%3A%20true%7D%5D)<br>
(Note: this uses the `quay.io` container image)

#### Option 2: Manual STDIO installation

For the usage in your project, create a file called `.vscode/mcp.json` with
the following content.

```
{
    "inputs": [
        {
            "id": "lightspeed_client_id",
            "type": "promptString",
            "description": "Enter the Red Hat Lightspeed Client ID",
            "default": "",
            "password": true
        },
        {
            "id": "lightspeed_client_secret",
            "type": "promptString",
            "description": "Enter the Red Hat Lightspeed Client Secret",
            "default": "",
            "password": true
        }
    ],
    "servers": {
        "lightspeed-mcp": {
            "type": "stdio",
            "command": "podman",
            "args": [
                "run",
                "--env",
                "LIGHTSPEED_CLIENT_ID",
                "--env",
                "LIGHTSPEED_CLIENT_SECRET",
                "--interactive",
                "--rm",
                "ghcr.io/redhatinsights/red-hat-lightspeed-mcp:latest"
            ],
            "env": {
                "LIGHTSPEED_CLIENT_ID": "${input:lightspeed_client_id}",
                "LIGHTSPEED_CLIENT_SECRET": "${input:lightspeed_client_secret}"
            }
        }
    }
}
```

### Cursor

First check the [prerequisites](#prerequisites) section.

#### Option 1: One-click installation (easiest)

⚠️ Use **`Ctrl`/`Cmd`-click** to open in a **new tab**.<br>
Otherwise the tab will close after installation and you won't see the documentation anymore.<br>
[![Install with Podman in Cursor](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en/install-mcp?name=red-hat-lightspeed-mcp&config=eyJ0eXBlIjoic3RkaW8iLCJjb21tYW5kIjoicG9kbWFuIHJ1biAtLWVudiBMSUdIVFNQRUVEX0NMSUVOVF9JRCAtLWVudiBMSUdIVFNQRUVEX0NMSUVOVF9TRUNSRVQgLS1pbnRlcmFjdGl2ZSAtLXJtIHF1YXkuaW8vcmVkaGF0LXNlcnZpY2VzLXByb2QvaW5zaWdodHMtbWFuYWdlbWVudC10ZW5hbnQvaW5zaWdodHMtbWNwL3JlZC1oYXQtbGlnaHRzcGVlZC1tY3A6bGF0ZXN0IiwiZW52Ijp7IkxJR0hUU1BFRURfQ0xJRU5UX0lEIjoiIiwiTElHSFRTUEVFRF9DTElFTlRfU0VDUkVUIjoiIn19)<br>
(Note: this uses the `quay.io` container image)

#### Option 2: Manual STDIO installation

Cursor doesn't seem to support `inputs` you need to add your credentials in the config file.
To start the integration create a file `~/.cursor/mcp.json` with
```
{
  "mcpServers": {
    "lightspeed-mcp": {
        "type": "stdio",
        "command": "podman",
        "args": [
            "run",
            "--env",
            "LIGHTSPEED_CLIENT_ID",
            "--env",
            "LIGHTSPEED_CLIENT_SECRET",
            "--interactive",
            "--rm",
            "ghcr.io/redhatinsights/red-hat-lightspeed-mcp:latest"
        ],
        "env": {
            "LIGHTSPEED_CLIENT_ID": "",
            "LIGHTSPEED_CLIENT_SECRET": ""
        }
    }
  }
}
```

If you see the error `Some tools have naming issues and may be filtered out.`, see [Known Issues](#known-issues).

#### Option 3: Manual Streamable HTTP installation (advanced)

start the server:

```
podman run --net host --rm ghcr.io/redhatinsights/red-hat-lightspeed-mcp:latest http
```

then integrate using **service account credentials**:

```
{
    "mcpServers": {
        "lightspeed-mcp": {
            "type": "http",
            "url": "http://localhost:8000/mcp",
            "headers": {
                "lightspeed-client-id": "",
                "lightspeed-client-secret": ""
            }
        }
    }
}
```

or alternatively using a **JWT Bearer token**:

```
{
    "mcpServers": {
        "lightspeed-mcp": {
            "type": "http",
            "url": "http://localhost:8000/mcp",
            "headers": {
                "Authorization": "Bearer <YOUR_JWT_TOKEN>"
            }
        }
    }
}
```

### Gemini CLI

First check the [prerequisites](#prerequisites) section.

#### Option 1: Manual STDIO installation
To start the integration create a file `~/.gemini/settings.json` with the following command:

```
{
    ...
    "mcpServers": {
        "lightspeed-mcp": {
            "type": "stdio",
            "command": "podman",
            "args": [
                "run",
                "--env",
                "LIGHTSPEED_CLIENT_ID=<YOUR_CLIENT_ID>",
                "--env",
                "LIGHTSPEED_CLIENT_SECRET=<YOUR_CLIENT_SECRET>",
                "--interactive",
                "--rm",
                "ghcr.io/redhatinsights/red-hat-lightspeed-mcp:latest"
            ]
        }
    }
}
```

#### Option 2: Manual Streamable HTTP installation (advanced)

start the server:

```
podman run --net host --rm ghcr.io/redhatinsights/red-hat-lightspeed-mcp:latest http
```

> [!NOTE]
> For podman machine on a mac you will need to set the host explicitly and expose the port
>
> ```
>   podman run -p 8000:8000 --rm ghcr.io/redhatinsights/red-hat-lightspeed-mcp:latest http --host 0.0.0.0
> ```

then integrate using **service account credentials**:

```
{
    ...
    "mcpServers": {
        "lightspeed-mcp": {
            "httpUrl": "http://localhost:8000/mcp",
            "headers": {
                "lightspeed-client-id": "<YOUR_CLIENT_ID>",
                "lightspeed-client-secret": "<YOUR_CLIENT_SECRET>"
            }
        }
    }
}
```

or alternatively using a **JWT Bearer token**:

```
{
    ...
    "mcpServers": {
        "lightspeed-mcp": {
            "httpUrl": "http://localhost:8000/mcp",
            "headers": {
                "Authorization": "Bearer <YOUR_JWT_TOKEN>"
            }
        }
    }
}
```

### Claude Desktop

First check the [prerequisites](#prerequisites) section.

For Claude Desktop there is an extension file in the [release section](https://github.com/RedHatInsights/insights-mcp/releases) of the project.

Just download the `red-hat-lightspeed-mcp*.mcpb` file (or `red-hat-lightspeed-mcp*.dxt` for legacy format) and add this in Claude Desktop with

`Settings -> Extensions -> Advanced Extensions Settings -> Install Extension…`

### CLine with VSCode

First check the [prerequisites](#prerequisites) section.

First off, start the SSE server with `sse` argument:

```bash
export LIGHTSPEED_CLIENT_ID=<YOUR_CLIENT_ID>
export LIGHTSPEED_CLIENT_SECRET=<YOUR_CLIENT_SECRET>
podman run --env LIGHTSPEED_CLIENT_ID --env LIGHTSPEED_CLIENT_SECRET --net host --rm ghcr.io/redhatinsights/red-hat-lightspeed-mcp:latest sse
```

In the `CLine -> Manage MCP Servers` interface, add a new server name and URL:
`http://localhost:9000/sse`. It shall create the following config:

```json
{
  "mcpServers": {
    "lightspeed-mcp": {
      "disabled": false,
      "type": "sse",
      "url": "http://localhost:9000/sse"
    }
  }
}
```

Ensure the `type` is `sse` as CLine does not support `HTTP` transport yet.

### Generic STDIO

First check the [prerequisites](#prerequisites) section.

For generic integration into other tools via STDIO, you should set the environment variables
`LIGHTSPEED_CLIENT_ID` and `LIGHTSPEED_CLIENT_SECRET` and use this command for an
integration using podman:

```bash
export LIGHTSPEED_CLIENT_ID=<YOUR_CLIENT_ID>
export LIGHTSPEED_CLIENT_SECRET=<YOUR_CLIENT_SECRET>
podman run --env LIGHTSPEED_CLIENT_ID --env LIGHTSPEED_CLIENT_SECRET --interactive --rm ghcr.io/redhatinsights/red-hat-lightspeed-mcp:latest
```

It is the MCP API what is exposed through standard input, not a chat interface.
You need an MCP client with "agent capabilities" to connect to the `red-hat-lightspeed-mcp` server and really use it.

#### Claude Code

First check the [prerequisites](#prerequisites) section.

Claude Code requires a slight change to the podman command, as the host environment is not
available when it runs. The credentials must be copied into the configuration instead, which
can be done with the following command after setting `LIGHTSPEED_CLIENT_ID` and
`LIGHTSPEED_CLIENT_SECRET` environment variables:

```bash
export LIGHTSPEED_CLIENT_ID=<YOUR_CLIENT_ID>
export LIGHTSPEED_CLIENT_SECRET=<YOUR_CLIENT_SECRET>
claude mcp add red-hat-lightspeed-mcp -- podman run --env LIGHTSPEED_CLIENT_ID=$LIGHTSPEED_CLIENT_ID --env LIGHTSPEED_CLIENT_SECRET=$LIGHTSPEED_CLIENT_SECRET --interactive --rm ghcr.io/redhatinsights/red-hat-lightspeed-mcp:latest
```

or just set the variables in the command directly:

```bash
claude mcp add red-hat-lightspeed-mcp -- podman run --env LIGHTSPEED_CLIENT_ID=<YOUR_CLIENT_ID> --env LIGHTSPEED_CLIENT_SECRET=<YOUR_CLIENT_SECRET> --interactive --rm ghcr.io/redhatinsights/red-hat-lightspeed-mcp:latest
```

To verify setup was successful, within the Claude terminal execute the command:
```bash
/mcp
```
If successful, you should see `red-hat-lightspeed-mcp` listed under Manage MCP servers with a green check mark connected status besides it.

### URL overrides

If you are using a non-standard RH Lightspeed URL, set the environment variables
* `LIGHTSPEED_BASE_URL`
* `LIGHTSPEED_SSO_BASE_URL`
* `LIGHTSPEED_PROXY_URL`
accordingly.

## Examples

This [blog post](https://developers.redhat.com/articles/2026/01/07/manage-ai-powered-inventory-using-red-hat-lightspeed#) has a few examples on how to use the RH Lightspeed MCP server.

You can also ask LLM you just attached to the MCP server to.
e.g.
```
Please explain red-hat-lightspeed-mcp and what I can do with it?
```

For example questions specific to each toolset please have a look at the test files:

 * [`image-builder-mcp`](src/image_builder_mcp/tests/test_llm_integration_easy.py#L20)
 * [`inventory-mcp`](src/inventory_mcp/test_prompts.md)
 * [`planning-mcp`](src/planning_mcp/test_prompts.md)
 * [`remediations-mcp`](src/remediations_mcp/test_prompts.md)
 * [`advisor-mcp`](src/advisor_mcp/test_prompts.md)
 * [`vulnerability-mcp`](src/vulnerability_mcp/test_prompts.md)

## CLI

For some use cases it might be needed to use the MCP server directly from the command line.
See [usage.md](usage.md) for the usage of the MCP server.

## Releases
There are two container images published for this MCP server.

 * `ghcr.io/redhatinsights/red-hat-lightspeed-mcp:latest`
 * `quay.io/redhat-services-prod/insights-management-tenant/insights-mcp/red-hat-lightspeed-mcp:latest`

They are both based on `main` branch and you can use either of them.

Insights-branded images are deprecated but still available for a while but might be removed in the future.

 * `ghcr.io/redhatinsights/insights-mcp:latest`
 * `quay.io/redhat-services-prod/insights-management-tenant/insights-mcp/insights-mcp:latest`


## Known Issues

### Cursor

When using Cursor with the MCP server, you might encounter the following error:

```
Some tools have naming issues and may be filtered out.

… exceeds 60 characters…
```

Please rename your MCP server name in the MCP configuration file (`mcp.json`) to a shorter name.


```
{
  "mcpServers": {
    "red-hat-lightspeed-mcp-this-will-be-too-long": { # <--- rename this
…
```

## Disclaimer

This software is provided "as is" without warranty of any kind, either express or implied. Use at your own risk. The authors and contributors are not liable for any damages or issues that may arise from using this software.

## Contributing
Please refer to the [hacking guide](HACKING.md) to learn more.
