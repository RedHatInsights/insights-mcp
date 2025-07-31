# Insights MCP - Developer Documentation

This document provides comprehensive information for AI assistants working with the Insights MCP codebase.

## Project Overview

**Insights MCP** is a Model Context Protocol (MCP) server that provides AI assistants with tools to interact with Red Hat Insights services, specifically the hosted Image Builder service. It enables creating, managing, and building custom Linux images through a structured API interface.

### Key Capabilities
- Create and manage Linux image blueprints
- Build custom images for various distributions (RHEL, CentOS, Fedora)
- Support multiple transport protocols (stdio, HTTP, SSE)
- OAuth and service account authentication
- Multi-client integration (Claude Desktop, VSCode, Cursor)

## Architecture

### Core Components

1. **ImageBuilderMCP Server** (`src/image_builder_mcp/server.py`)
   - Main MCP server inheriting from FastMCP
   - Manages tool registration and client dependencies
   - Handles authentication and client caching

2. **ImageBuilderClient** (`src/image_builder_mcp/client.py`)
   - HTTP client for Red Hat Image Builder API
   - Token management and authentication
   - API request handling with error management

3. **OAuth Middleware** (`src/image_builder_mcp/oauth.py`)
   - Starlette middleware for OAuth flows
   - Dynamic client registration
   - Metadata proxying for MCP compatibility

### Transport Modes

The server supports three transport protocols:

- **STDIO** (default): Direct process communication for desktop integrations
- **HTTP**: RESTful API with streaming capabilities  
- **SSE**: Server-sent events for real-time web clients

## Development Setup

### Prerequisites
- Python 3.8+ (3.13+ recommended)
- `uv` package manager (recommended) or standard Python `venv` + `pip`
- Podman or Docker
- Red Hat console access for service account credentials

### Installation

**Recommended approach using `uv`:**

1. **Create virtual environment:**
   ```bash
   uv venv
   source .venv/bin/activate
   ```

2. **Install in development mode:**
   ```bash
   uv pip install -e .
   ```

3. **Install all development dependencies:**
   ```bash
   uv pip install -e .[dev]
   ```

**Alternative approach using standard Python tools:**

1. **Create virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. **Install in development mode:**
   ```bash
   pip install -e .
   ```

3. **Install development dependencies:**
   ```bash
   pip install -e .[dev]
   # or
   make install-test-deps
   ```

4. **Set up authentication:**
   - Go to https://console.redhat.com
   - Navigate to 'YOUR USER' → My User Access → Service Accounts
   - Create a service account and set environment variables:
     ```bash
     export INSIGHTS_CLIENT_ID="your-client-id"
     export INSIGHTS_CLIENT_SECRET="your-client-secret"
     ```

### Running the Server

**Development mode (stdio):**
```bash
image-builder-mcp
```

**HTTP transport:**
```bash
image-builder-mcp http --port 8000
```

**SSE transport:**
```bash
image-builder-mcp sse --port 9000
```

**Using containers:**
```bash
make run-stdio   # STDIO mode
make run-http    # HTTP streaming
make run-sse     # Server-sent events
```

## Testing

### Test Structure

- `tests/` - Main test directory with auth and utility tests
- `src/image_builder_mcp/tests/` - Component-specific tests
- LLM integration tests using deepeval framework

### Running Tests

**Basic test execution:**
```bash
make test                # Standard test run
make test-verbose        # With logging output
make test-very-verbose   # With debug output
make test-coverage       # With coverage reporting
```

**Manual pytest execution:**
```bash
env DEEPEVAL_TELEMETRY_OPT_OUT=YES pytest -v
```

### Test Configuration

1. **Copy example configuration:**
   ```bash
   cp test_config.json.example test_config.json
   ```

2. **Configure LLM models** in `test_config.json`:
   ```json
   {
     "llm_configurations": [{
       "name": "Primary Model",
       "MODEL_ID": "granite-3.1",
       "MODEL_API": "https://your-vLLM-server",
       "USER_KEY": "your-api-key"
     }],
     "guardian_llm": {
       "name": "Evaluation Model",
       "MODEL_ID": "granite-3.2",
       "MODEL_API": "https://your-vLLM-server2",
       "USER_KEY": "your-api-key"
     }
   }
   ```

### Test Types

- **Unit Tests**: Component isolation and API method validation
- **Integration Tests**: End-to-end workflow testing
- **LLM Behavioral Tests**: Validates AI assistant interaction patterns
- **Multi-Transport Tests**: Validates across stdio/HTTP/SSE modes

## Code Quality & Linting

### Pre-commit Hooks
```bash
make lint    # Run all linting with pre-commit
```

### Manual Tools
```bash
pylint src/                    # Code analysis
mypy src/                      # Type checking  
autopep8 --in-place src/       # Code formatting
```

### Configuration
- **Line length**: 120 characters (pyproject.toml)
- **Type checking**: mypy with strict settings
- **Code style**: autopep8 with 120 char limit

## Available MCP Tools

The server provides 9 tools categorized by behavior:

### Information Retrieval (🟢 - Safe to call immediately)
1. `get_openapi` - API schema and capabilities
2. `get_blueprints` - List user blueprints (pagination, search)
3. `get_blueprint_details` - Detailed blueprint info by UUID
4. `get_composes` - List image builds with status
5. `get_compose_details` - Build details and download URLs
6. `get_distributions` - Available Linux distributions

### Creation/Modification (🔴 - Gather information first)
7. `create_blueprint` - Create new image blueprint
8. `update_blueprint` - Modify existing blueprint  
9. `blueprint_compose` - Start image build from blueprint

### Tool Usage Guidelines
- Always call information tools before creation tools
- Validate parameters using schema from `get_openapi`
- Follow color-coded behavioral hints in tool descriptions

## Integration Patterns

### Claude Desktop
```json
{
  "servers": {
    "insights-mcp-stdio": {
      "type": "stdio",
      "command": "podman",
      "args": ["run", "--env", "INSIGHTS_CLIENT_ID", ...],
      "env": {
        "INSIGHTS_CLIENT_ID": "${input:insights_client_id}",
        "INSIGHTS_CLIENT_SECRET": "${input:insights_client_secret}"
      }
    }
  }
}
```

### VSCode (.vscode/mcp.json)
- Secure credential prompting
- Container-based execution
- Workspace-specific configuration

### Cursor (~/.cursor/mcp.json)  
- Static credential configuration
- HTTP transport support
- Network host mode for streaming

## Environment Variables

### Required
- `INSIGHTS_CLIENT_ID` - Red Hat service account client ID
- `INSIGHTS_CLIENT_SECRET` - Red Hat service account secret

### Optional
- `IMAGE_BUILDER_MCP_DISABLE_DESCRIPTION_WATERMARK=True` - Disable blueprint watermarks
- `DEEPEVAL_TELEMETRY_OPT_OUT=YES` - Disable telemetry in tests

## Security Considerations

- **Credential Management**: Use environment variables, never hardcode secrets
- **Container Isolation**: Recommended deployment method  
- **OAuth Support**: Available for hosted deployments
- **Token Management**: Automatic refresh with 5-minute buffer
- **Transport Security**: HTTPS for production HTTP/SSE modes

## Common Development Tasks

### Adding New Tools
1. Define tool method in `ImageBuilderMCP` class
2. Add type annotations and parameter validation
3. Use `@expose` decorator with appropriate parameters
4. Add behavioral color coding (🟢/🔴)
5. Write unit and integration tests

### Debugging Authentication
- Check service account credentials in Red Hat console
- Verify environment variables are set correctly
- Enable verbose logging: `logging.basicConfig(level=logging.DEBUG)`
- Use `make test-very-verbose` for detailed auth flow logs

### Building Containers
```bash
make build      # Local development image
make build-prod # Production image with upstream tag
```

### Cleaning Up
```bash
make clean-test  # Remove test artifacts and cache
```

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Verify service account credentials
   - Check token expiration (auto-refreshed)
   - Ensure network access to sso.redhat.com

2. **Container Build Issues**  
   - Check podman/docker installation
   - Verify container runtime permissions
   - Use `make build` for local development

3. **Test Failures**
   - Ensure test dependencies installed: `make install-test-deps`
   - Check LLM configuration in `test_config.json`
   - Verify network access for integration tests

4. **Transport Issues**
   - STDIO: Check container interactive mode
   - HTTP/SSE: Verify port availability and firewall rules
   - OAuth: Ensure proper middleware configuration

### Debug Commands
```bash
# Server debug mode
image-builder-mcp --log-level DEBUG

# Test with verbose output  
make test-very-verbose

# Container debug
podman run -it --rm insights-mcp /bin/bash
```

## Contributing Guidelines

1. **Code Style**: Follow existing patterns, 120-char line limit
2. **Testing**: Add tests for new functionality
3. **Documentation**: Update this file for architectural changes
4. **Security**: Never commit credentials or sensitive data
5. **Containers**: Test both podman and docker compatibility

## Dependencies

### Runtime
- `fastmcp>=2.10.1` - MCP server framework
- `requests` - HTTP client library
- `PyJWT` - JWT token handling

### Development  
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `mypy` - Type checking
- `pylint` - Code analysis
- `deepeval` - LLM evaluation
- `llama-index` - LLM integration testing

This documentation should be sufficient for AI assistants to understand the codebase architecture, development workflows, and contribution patterns for the Insights MCP project.
