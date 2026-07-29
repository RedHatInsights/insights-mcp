# Insights MCP Contributing Guide

## Run

⚠️ Usually you want to just use the MCP server via a tool like VSCode, Cursor, etc.
so please refer to the [integrations](README.md#integrations) section unless you want to
develop the MCP server.

Also checkout `make help` for the available commands.

## Testing

The majority of tests are automatically run by CI/CD pipelines or
locally by running `make test`.

Although there are tests to use the `main` code, to double check that
especially handing over environment variables and credentials
(in multiple ways) work, those are the use cases that should be working:

### STDIO Mode (see `make run-stdio`)
- Default configuration with credentials in environment variables
- Custom environment: `INSIGHTS_BASE_URL`, `INSIGHTS_PROXY_URL`, and `INSIGHTS_SSO_BASE_URL` set with credentials in environment variables

### Streaming HTTP Mode (see `make run-http`)
- Default configuration with service account credentials in header (`insights-client-id` / `insights-client-secret`)
- Default configuration with JWT Bearer token in `Authorization: Bearer <token>` header
- Custom environment: `INSIGHTS_BASE_URL`, `INSIGHTS_PROXY_URL`, and `INSIGHTS_SSO_BASE_URL` set with credentials in header

### SSE HTTP Mode (deprecated but some MCP clients still need this, see `make run-sse`)
- Default configuration with service account credentials in header or JWT Bearer token
- Custom environment: `INSIGHTS_BASE_URL` and `INSIGHTS_SSO_BASE_URL` set with credentials in header

## Architecture

### Application Structure

The `InsightsMCPServer` acts as a unified server that mounts multiple specialized MCP toolsets. Each toolset extends `InsightsMCP` and provides tools for specific Red Hat Insights services.

```mermaid
%% title: architecture-structure
graph TB
    MCP[MCP Interface<br/>stdio/HTTP/SSE]
    subgraph "InsightsMCPServer"
        MainServer[InsightsMCPServer<br/>FastMCP]
        MainServer -->|mounts| ImageBuilder[ImageBuilderMCP<br/>image-builder_*]
        MainServer -->|mounts| Vulnerability[VulnerabilityMCP<br/>vulnerability_*]
        MainServer -.->|mounts| More[other MCPs<br/>...]
    end
    subgraph "HTTP Client Layer"
        InsightsClient[InsightsClient<br/>factory]
        OAuth2Client[InsightsOAuth2Client<br/>direct OAuth]
        HeadersClient[InsightsHeadersBasedClient<br/>multiuser auth]
        BearerClient[InsightsBearerTokenClient<br/>JWT bearer token]
        SessionCache[SessionCache<br/>token caching]
        InsightsClientBase[InsightsClientBase<br/>HTTP operations]

        InsightsClient -->|creates| OAuth2Client
        InsightsClient -->|creates| HeadersClient
        HeadersClient -->|uses| SessionCache
        HeadersClient -->|creates| BearerClient
        OAuth2Client -->|extends| InsightsClientBase
        BearerClient -->|extends| InsightsClientBase
        HeadersClient -->|uses| OAuth2Client
    end
    API[Red Hat Insights<br/>REST API]

    MCP -->|connects| MainServer
    ImageBuilder -->|uses| InsightsClient
    Vulnerability -->|uses| InsightsClient
    More -.->|uses| InsightsClient
    InsightsClientBase -->|calls| API

    style MainServer fill:#e1f5ff
    style ImageBuilder fill:#fff4e1
    style Vulnerability fill:#fff4e1
    style More fill:#fff4e1
    style InsightsClient fill:#f3e5f5
    style OAuth2Client fill:#f3e5f5
    style HeadersClient fill:#f3e5f5
    style BearerClient fill:#f3e5f5
    style SessionCache fill:#ffe5f5
    style InsightsClientBase fill:#f3e5f5
    style MCP fill:#e8f5e9
    style API fill:#fff3e0
```

Here is the rendered version: [Application Structure](docs/architecture-structure.svg)

### Deployment Flow

MCP clients (like VSCode or Cursor) communicate with the `insights-mcp` server, which in turn makes authenticated requests to Red Hat Insights REST APIs.

```mermaid
%% title: architecture-deployment
sequenceDiagram
    participant Client as MCP Client<br/>(VSCode/Cursor)
    box rgb(225, 245, 255)
    participant Server as insights-mcp<br/>Server
    end
    participant SSO as Red Hat SSO<br/>(OAuth2)
    participant API as Red Hat Insights<br/>REST API

    Client->>Server: MCP Protocol<br/>(stdio/HTTP/SSE)
    Server->>SSO: Authenticate<br/>(OAuth2)
    SSO-->>Server: Auth Token
    Server->>API: HTTP Request<br/>(with auth token)
    API-->>Server: JSON Response
    Server-->>Client: MCP Response
```

Here is the rendered version: [Deployment Flow](docs/architecture-deployment.svg)

**Note**: To regenerate the `SVG` diagram images, run `make generate-docs`. The diagrams are also rendered directly by GitHub when viewing this file.

### Session Cache and Token Management

For multiuser scenarios (SSE/HTTP transports with header-based authentication), the `SessionCache` component provides per-connection OAuth token caching to improve performance and reduce authentication overhead.

**Key features:**
- Cache key: `(session_id, credentials_hash)` ensures isolation between connections and credential sets
- Default TTL: 15 minutes with automatic expiration
- Periodic cleanup: Removes expired entries every 20 minutes
- Thread-safe: Supports concurrent access from multiple requests

**Implementation:** See [`src/insights_mcp/session_cache.py`](src/insights_mcp/session_cache.py)

**Used by:** `InsightsHeadersBasedClient` for SSE/HTTP transports when service account credentials are provided via request headers. JWT Bearer token authentication bypasses the cache since no token exchange is needed.

## MCP Apps

[MCP Apps](https://modelcontextprotocol.io/extensions/apps/overview) is an MCP extension (`io.modelcontextprotocol/ui`) that lets MCP servers return interactive HTML interfaces (data visualizations, forms, dashboards) that render directly in the chat. Clients with MCP Apps support include Cursor, VS Code Copilot, Claude Desktop, and [others](https://modelcontextprotocol.io/extensions/client-matrix). CLI and TUI clients (e.g. Claude Code, Copilot CLI, OpenCode) do not support UI rendering.

### How It Works

1. The server registers an HTML page as a **UI resource** (`@mcp.resource`).
2. The server registers a **tool that references it** (`@mcp.tool` with `AppConfig`).
3. When a client calls the tool, the server returns a `ToolResult` with `content` and `structured_content`. To handle clients that don't support UI rendering, the server can use `ctx.client_supports_extension(UI_EXTENSION_ID)` to detect support and adapt the response accordingly.
4. The app HTML connects to the MCP Apps SDK and can interact with the server in two ways:
   - Via `ontoolresult` — receives the tool call result.
   - Via `callServerTool` — invokes MCP tools directly from the HTML (e.g. to fetch additional data or drill into details).

### Adding a New MCP App

#### 1. Create the HTML template and dashboard-specific CSS

Create `src/<toolset_mcp>/<app_name>.html` and `src/<toolset_mcp>/<app_name>.css`.

The HTML template uses placeholders that get replaced at load time with shared assets:

- `/* __DASHBOARD_BASE_CSS__ */` — shared base CSS (themes, layout, buttons, severity badges, pagination)
- `/* __DASHBOARD_EXTRA_CSS__ */` — dashboard-specific CSS from the `.css` file
- `/* __DASHBOARD_COMMON_JS__ */` — shared JS utilities (`callTool`, `showError`, `severityLabel`, `connectMcpApp`, etc.)
- `<!-- __DASHBOARD_ICON__ -->` — Red Hat icon `<img>` tag

Shared assets live in `src/insights_mcp/assets/` (`dashboard_base.css`, `dashboard_common.js`). Dashboard-specific styles go in the `.css` file alongside the template. Use CSS variables from the base CSS (e.g., `var(--text-primary)`, `var(--border-light)`) — never hardcode theme-dependent colors in templates or inline styles.

Use `connectMcpApp()` from the common JS instead of manually loading the MCP Apps SDK:

```javascript
connectMcpApp("My App", "1.0.0", (query) => fetchMyData(query));
```

#### 2. Load the HTML at module level

In `src/<toolset_mcp>/server.py`:

```python
from insights_mcp.dashboard_ui import load_dashboard_html

EMBEDDED_MY_APP_HTML = load_dashboard_html(
    "my_toolset_mcp",
    "my_app.html",
    "my_app.css",
)
```

Update `pyproject.toml` to include the new file types in `[tool.setuptools.package-data]`:

```toml
my_toolset_mcp = ["*.html", "*.css"]
```

#### 3. Define resource and mounted URIs

```python
MY_APP_RESOURCE_URI = "ui://my-app"
MY_APP_MOUNTED_URI = "ui://my_toolset_/my-app"
```

The mounted URI follows the convention `ui://<toolset_name>_/<app-name>`, matching how FastMCP mounts toolset tools.

#### 4. Register the resource

```python
from fastmcp.apps import AppConfig, ResourceCSP

@mcp.resource(
    MY_APP_RESOURCE_URI,
    app=AppConfig(csp=ResourceCSP(resource_domains=["https://unpkg.com"])),
)
def my_app_ui() -> str:
    """My App UI description."""
    return EMBEDDED_MY_APP_HTML
```

Since the HTML is embedded in the Python package, external dependencies like PatternFly CSS should be loaded from a CDN rather than bundled inline. The `ResourceCSP` whitelist must include any CDN domains used.

#### 5. Register the tool with a UI resource

```python
from fastmcp import Context
from fastmcp.apps import UI_EXTENSION_ID, AppConfig
from fastmcp.tools import ToolResult

@mcp.tool(
    annotations={"readOnlyHint": True},
    app=AppConfig(resource_uri=MY_APP_MOUNTED_URI),
)
async def load_my_app(ctx: Context, ...) -> ToolResult:
    """Render data in the interactive app."""
    ui_supported = ctx.client_supports_extension(UI_EXTENSION_ID)
    if not ui_supported:
        return ToolResult(
            content="Client does not support MCP Apps.",  # fallback instructions for non-UI clients
        )
    return ToolResult(
        content="...",  # optional message for the model (also available for the HTML via result.content)
        structured_content={...},  # data for the HTML via result.structuredContent
    )
```


#### 6. Connect the HTML to MCP Apps SDK

> **Dark mode:** The shared base CSS defines CSS variables on `:root` (light) and `[data-theme="dark"]` (dark). The `connectMcpApp()` utility from `dashboard_common.js` handles theme switching automatically. Use `background: transparent` on body to inherit the host app's background. Use CSS variables (e.g., `var(--text-secondary)`) — never hardcode theme-dependent colors.

The shared `dashboard_common.js` (injected via the `/* __DASHBOARD_COMMON_JS__ */` placeholder) provides:

- `connectMcpApp(appName, version, onToolResult)` — loads the MCP Apps SDK, handles theme, wires `ontoolresult`
- `callTool(name, args)` — wraps `callServerTool` with error handling and JSON parsing
- `showError(msg)` / `hideError()` — alert banner management
- `severityLabel(impact)` / `severityClass(impact)` — severity badge mapping
- `renderPageButtons(current, total, containerEl)` — pagination with ellipsis
- `escapeHtml(str)` — HTML escaping

```html
<script type="module">
/* __DASHBOARD_COMMON_JS__ */

    connectMcpApp("My App", "1.0.0", (query) => fetchMyData(query));

    async function fetchMyData(query) {
        const result = await callTool("my_toolset__my_tool", { param: query.param });
        // render result
    }
</script>
```

#### 7. Calling tools from the app

Apps can invoke MCP tools directly for drill-downs or fetching additional data. Only tools on the same MCP server as the resource can be called — cross-server tool calls are not supported.

```javascript
const result = await window.mcpApp.callServerTool({
    name: "toolset__tool_name",
    arguments: { param: "value" }
});
const text = result.content?.find(c => c.type === "text")?.text;
```

#### 8. Add test prompts

Add 1-2 example prompts to `src/<toolset_mcp>/test_prompts.md` that exercise the app.

### Design Resources

- [PatternFly](https://www.patternfly.org/) — CSS framework used for styling MCP Apps in this project

### Shared Dashboard Assets

Shared CSS and JS live in [`src/insights_mcp/assets/`](src/insights_mcp/assets/):

- [`dashboard_base.css`](src/insights_mcp/assets/dashboard_base.css) — theme variables, layout, buttons, severity badges, pagination, filters
- [`dashboard_common.js`](src/insights_mcp/assets/dashboard_common.js) — `callTool`, `showError`, `severityLabel`, `connectMcpApp`, etc.

The composition helper [`src/insights_mcp/dashboard_ui.py`](src/insights_mcp/dashboard_ui.py) replaces placeholders in HTML templates with these shared assets, producing self-contained HTML for MCP Apps.

### Existing Apps

Use these as reference implementations:

- **CVE Dashboard**: [`cve_dashboard.html`](src/vulnerability_mcp/cve_dashboard.html) + [`cve_dashboard.css`](src/vulnerability_mcp/cve_dashboard.css) + [`server.py`](src/vulnerability_mcp/server.py)
- **Inventory Dashboard**: [`inventory_dashboard.html`](src/inventory_mcp/inventory_dashboard.html) + [`inventory_dashboard.css`](src/inventory_mcp/inventory_dashboard.css) + [`server.py`](src/inventory_mcp/server.py)

## Important notes
* When changing some code you might want to use `make build-prod` so the container is built with
  the upstream container tag and you don't need to change it in your MCP client (like VSCode).

* Make sure you really restart VSCode or Cursor after changing the code, as their "restart" button
  usually doesn't use the newly built container.

* ⚠️ Moreover, when you start VSCode, make sure you hit the `▶️ Start` button of the MCP server,
  **before** you start chatting! Otherwise VSCode _caches_ the tool descriptions and you will
  end up with a chat context with the old tool descriptions!

## Testing/local OpenID Connect (OIDC)

For tests you can override `INSIGHTS_BASE_URL`, `INSIGHTS_SSO_BASE_URL`.


### Usage

See [usage.md](usage.md) for the usage of the MCP server.

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
uv sync --locked --all-extras --dev
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


## Hosted MCP Server with Auth Provider (HTTP transport)

When deploying the MCP server as a hosted service over HTTP/SSE, token validation is handled by
[`mcp_rh_auth`](src/mcp_rh_auth/README.md) via `build_auth_provider()`.
When `AUTH_SERVER` is unset, no auth provider is configured and the server falls back to raw
Bearer token pass-through (backward-compatible with self-hosted and stdio deployments).

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `AUTH_SERVER` | Yes | OAuth authorization server base URL (e.g. `https://sso.redhat.com/auth/realms/redhat-external`) |
| `AUTH_ISSUER` | Yes | JWT `iss` claim — must match the SSO realm issuer |
| `MCP_BASE_URL` | Yes (hosted) | Public base URL of this MCP server (used in `/.well-known/oauth-protected-resource`); no default — must be set for hosted deployments |
| `AUTH_RESOURCE` | No | MCP server resource URL; defaults to `{MCP_BASE_URL}/mcp` if unset |
| `AUTH_SCOPES` | No | Comma-separated required scopes (default: `api.graphql`) |
| `AUTH_AUDIENCE` | No | Comma-separated accepted JWT audiences |
| `AUTH_JWKS_URI` | No | Override JWKS endpoint (otherwise fetched from `AUTH_SERVER` discovery document) |

### How it works

1. `build_auth_provider()` fetches the OIDC discovery document from `AUTH_SERVER` to resolve the JWKS URI and issuer.
2. FastMCP validates the `Authorization: Bearer <token>` header on every HTTP request against the JWKS.
3. The validated token is retrieved via `get_access_token()` and forwarded to the Insights API.
4. If `AUTH_SERVER` is unset, the token is extracted directly from the `Authorization` header without server-side validation (existing behavior).

### Example configuration

```bash
export AUTH_SERVER="https://sso.redhat.com/auth/realms/redhat-external"
export AUTH_ISSUER="https://sso.redhat.com/auth/realms/redhat-external"
export AUTH_SCOPES="openid,api.console,api.ocm"
# For production: set MCP_BASE_URL to the public URL of this server
# export MCP_BASE_URL="https://your-mcp-server.example.com"

uv run insights-mcp http --host 0.0.0.0 --port 8000
```

## Logging and Compliance

### Debug Mode

Debug logging (`--debug` or `INSIGHTS_MCP_DEBUG=1`) includes identifiers such as client IDs and request metadata for troubleshooting. **Do not enable debug mode in production.** Debug logs may be retained by log aggregation systems; restricting debug to development and staging supports ISO 27001 (A.5.17, A.8.11) and ISO 27018 (PII protection).

### Logging and Monitoring

- **Default (INFO)**: Auth events, errors, and request metadata. Client secrets and PII in SSO claims are masked.
- **Debug**: Additional identifiers (client IDs, scopes, org_id). PII (account_id, username, email) remains masked.
- **Retention**: Operators should configure log aggregation and retention per their policy (ISO 27001 A.8.16).

### Deployment Responsibilities

For cloud deployments, the shared responsibility model applies (ISO 27017):

- **Red Hat**: API security, availability, authentication.
- **Operator**: MCP server deployment, credential protection, network isolation, incident response (see [README Security & Incident Response](README.md#security--incident-response-emergency-revocation)).

### AI Governance Scope

The MCP server is an AI-enabling component (connects LLMs to Red Hat services). Operators using it for AI workflows should include it in their AI governance scope (e.g., ISO 42001 AIMS) and risk assessments.


## Pipelines as Code configuration
To start the PipelineRun, add a new comment in a pull-request with content `/ok-to-test`

If a test fails, add a new comment in a pull-request with content `/retest` to re-run the test.

For more detailed information about running a PipelineRun, please refer to Pipelines as Code documentation [Running the PipelineRun](https://pipelinesascode.com/docs/guide/running/)

To customize the proposed PipelineRuns after merge, please refer to [Build Pipeline customization](https://konflux-ci.dev/docs/building/customizing-the-build/)

Please follow the block sequence indentation style introduced by the proposed PipelineRuns YAMLs, or keep using consistent indentation level through your customized PipelineRuns. When different levels are mixed, it will be changed to the proposed style.
