# Insights MCP

This repo is in a DRAFT and playground state!

An MCP server to interact with insights services like the
 * [hosted image builder](https://osbuild.org/docs/hosted/architecture/)

## Authentication

Go to https://console.redhat.com to `'YOUR USER' ➡ My User Access ➡ Service Accounts` create a service account
and then set the environment variables `INSIGHTS_CLIENT_ID` and `INSIGHTS_CLIENT_SECRET` accordingly.

### ⚠️ Security Remarks ⚠️

If you start this MCP server locally (with `podman` or `docker`) make sure the container is not exposed to the internet. In this scenario it's probably fine to use `INSIGHTS_CLIENT_ID` and `INSIGHTS_CLIENT_SECRET` although your MCP Client (e.g. VSCode, Cursor, etc.) can get your `INSIGHTS_CLIENT_ID` and `INSIGHTS_CLIENT_SECRET`.

For a deployment where you connect to this MCP server from a different machine, you should consider that `INSIGHTS_CLIENT_ID` and `INSIGHTS_CLIENT_SECRET` are transferred to the MCP server and you are trusting the remote MCP server not to leak them.

In both cases if you are in doubt, please disable/remove the `INSIGHTS_CLIENT_ID` and `INSIGHTS_CLIENT_SECRET` from your account after you are done using the MCP server.

## Run

### Using Python directly

#### Option 1: Global CLI tool (recommended for usage)
Install as a global CLI tool (lighter, no development dependencies):

```bash
uv tool install -e .
```

Then run directly:

```bash
insights-mcp sse
```

#### Option 2: Project environment (recommended for development)
Set up the development environment (includes development dependencies for testing, linting, etc.):

```bash
uv sync --all-extras --dev
```

Then run with `uv`:

```bash
uv run insights-mcp sse
```

**Note**: Use Option 2 if you need to run tests, linting, or other development tasks:
```bash
uv run pytest
uv run mypy src/
uv run pylint src/
```

Both approaches will start `insights-mcp` server at http://localhost:9000/sse

For HTTP streaming transport:

```bash
insights-mcp http
```

This will start `insights-mcp` server with HTTP streaming transport at http://localhost:8000/mcp

### Using Podman/Docker

You can also copy the command from the [Makefile]
For SSE mode:
```
make run-sse
```

For HTTP streaming mode:
```
make run-http
```

You can also copy the command from the [Makefile]
For stdio mode:
```
make run-stdio
```

### Additional info

You can set the environment variable `IMAGE_BUILDER_MCP_DISABLE_DESCRIPTION_WATERMARK` to `True` to avoid adding a hint to newly created image builder blueprints.

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
            "type": "Streamable HTTP",
            "url": "http://localhost:8000/mcp/",
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

## Contributing
Please refer to the [hacking guide](HACKING.md) to learn more.
