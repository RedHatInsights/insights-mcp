# Insights MCP - AI Coding Assistant Guide

This document provides AI coding assistants with specific guidance for working with the Insights MCP codebase. **Start by reading [README.md](README.md)** for project overview, authentication setup, and client integrations.

This guide supplements the README with development-specific information and workflow guidance for AI coding assistants.

## Architecture

### Core Components

1. **InsightsMCPServer** (`src/insights_mcp/server.py`)
   - Main unified server that mounts multiple service toolsets
   - Handles authentication and configuration for all mounted toolsets
   - Supports selective toolset registration via `--toolset` argument

2. **InsightsMCP Base Class** (`src/insights_mcp/mcp.py`)
   - Abstract base class for all Insights MCP toolsets
   - Manages authentication and client initialization
   - Provides common functionality for Red Hat Insights API integration

3. **InsightsClient** (`src/insights_mcp/client.py`)
   - HTTP client for Red Hat Insights APIs with OAuth2 support
   - Handles service account and refresh token authentication
   - Provides error handling and proxy support

4. **OAuth Middleware** (`src/insights_mcp/oauth.py`)
   - Starlette middleware for OAuth flows in HTTP/SSE transports
   - Dynamic client registration and metadata proxying

### Toolset Architecture

The project uses a **toolset-based architecture** where each service is implemented as a separate toolset:

**Toolset Implementation Pattern:**
- Most toolsets: `src/<toolset_name>_mcp/server.py` (e.g., `src/vulnerability_mcp/server.py`)
- Legacy pattern: `src/insights_mcp/servers/<name>.py` (e.g., example toolset)

**Example toolsets (see `src/insights_mcp/server.py` MCPS list for complete current list):**
- **image-builder** (`src/image_builder_mcp/server.py`): Linux image building tools
- **vulnerability** (`src/vulnerability_mcp/server.py`): Security vulnerability management
- **inventory** (`src/inventory_mcp/server.py`): System inventory management

**Toolset Registration:**
- Toolsets are registered in `MCPS` list in `src/insights_mcp/server.py`
- Each toolset has a unique `toolset_name` for identification
- Tools are mounted with toolset prefix (e.g., `image-builder_get_blueprints`)
- Users can select specific toolsets: `insights-mcp --toolset=image-builder`

### Transport Modes

- **STDIO** (default): Direct process communication for desktop integrations
- **HTTP**: RESTful API with streaming capabilities  
- **SSE**: Server-sent events for real-time web clients

## Development Workflow for AI Assistants

### Quick Setup
```bash
# Prerequisites: Python 3.10+, uv package manager
uv venv && source .venv/bin/activate
make install-test-deps  # Installs all dev dependencies
```

### Essential Commands
```bash
make help  # Show all available make targets
```

**Key development commands:**
- `make test` - Run test suite
- `make lint` - Run all linting
- `make build` - Build container image
- `insights-mcp` - Run server in development mode

**Note**: Commands require `source .venv/bin/activate` first.
**Note**: Authentication setup is covered in [README.md](README.md).

## Testing

### Test Structure

**General pattern for toolset testing:**
- `tests/` - Main test directory with cross-toolset auth and utility tests
- `src/<toolset_name>_mcp/tests/` - Toolset-specific tests (when present)
- `src/<toolset_name>_mcp/test_prompts.md` - Test prompts for LLM validation

**Example test implementations:**
- `tests/` - Cross-toolset authentication, API, and pattern tests
- `src/image_builder_mcp/tests/` - Full test suite with unit and LLM integration tests  
- `src/vulnerability_mcp/test_prompts.md` - LLM test prompts (pattern used by most toolsets)

### Running Tests

**Available test targets:**
```bash
make help  # Shows all available targets with descriptions
```

**Key test commands (see `make help` for complete list):**
- `make test` - Standard test run
- `make test-verbose` - With logging output  
- `make test-coverage` - With coverage reporting
- `make install-test-deps` - Install test dependencies

**Manual pytest execution:**
```bash
env DEEPEVAL_TELEMETRY_OPT_OUT=YES uv run pytest -v
```

see also [usage.md](usage.md) for more details on the CLI.

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
make lint    # Run all linting with pre-commit (requires pre-commit installation)
```

**Note:** The `make lint` command requires pre-commit to be installed. If you encounter "pre-commit: No such file or directory", install it first:
```bash
uv add --dev pre-commit  # or pip install pre-commit
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

## Available Toolsets and Tools

### Dynamic Tool Discovery

The available toolsets are listed in [toolsets.md](toolsets.md).

**To discover tools for a specific toolset:**
1. Start the server: `insights-mcp --toolset=<toolset-name>`
2. Use MCP client tool discovery (e.g., in Claude Desktop, tools appear automatically)
3. Call `<toolset-name>_get_openapi` for detailed API schema and tool descriptions

### Toolset Examples

**Example toolsets (not exhaustive):**
- **remediations**: System remediation tools
- **advisor**: System advisory tools  
- **vulnerability**: Security vulnerability management

**Tool Naming Convention:**
- Tools are prefixed with toolset name: `<toolset-name>_<tool-name>`
- Examples: `image-builder_get_blueprints`, `vulnerability_get_cves`, `inventory_get_systems`

**Tool Usage Guidelines:**
- Always call information tools before creation tools
- Validate parameters using schema from `get_openapi`
- Follow color-coded behavioral hints in tool descriptions (🟢 safe to call, 🔴 gather info first)

**Toolset Selection:**
```bash
insights-mcp --toolset=image-builder              # Only image builder tools
insights-mcp --toolset=vulnerability              # Only vulnerability tools  
insights-mcp --toolset=all                        # All available toolsets (default)
insights-mcp --toolset=image-builder,vulnerability # Multiple specific toolsets
```

## Client Integration Notes

**Full integration examples are in [README.md](README.md)**. Key points for AI assistants:

- **VSCode**: Uses `.vscode/mcp.json` with secure credential prompting
- **Cursor**: Uses `~/.cursor/mcp.json`, supports both stdio and HTTP transport
- **Claude Desktop**: Extension available in releases, installed via `.mcpb` or `.dxt` file
- **Generic STDIO**: Use container with environment variables

## Environment Variables

**Authentication variables are documented in [README.md](README.md)**. Development-specific variables:

- `IMAGE_BUILDER_MCP_DISABLE_DESCRIPTION_WATERMARK=True` - Disable blueprint watermarks  
- `DEEPEVAL_TELEMETRY_OPT_OUT=YES` - Disable telemetry in tests

## Security Notes for Development

**See [README.md](README.md) for security considerations**. For development:
- Never hardcode credentials in code
- Use environment variables for secrets
- Container isolation recommended

## Common Development Tasks

### Adding New Toolsets
1. Create new class inheriting from `InsightsMCP` in `src/insights_mcp/servers/`
2. Set unique `toolset_name` and appropriate `api_path`
3. Implement tools using `@mcp.tool()` decorator
4. Add toolset to `MCPS` list in `src/insights_mcp/server.py`
5. Write unit and integration tests

### Adding New Tools to Existing Toolsets
1. Define tool method in the toolset class (e.g., `ImageBuilderMCP`)
2. Use `@expose` decorator for FastMCP or method definition for toolset pattern
3. Add type annotations and parameter validation
4. Add behavioral color coding (🟢/🔴) in descriptions
5. Write unit and integration tests

### Debugging Authentication
- Check service account credentials in Red Hat console
- Verify environment variables are set correctly
- Enable verbose logging: `logging.basicConfig(level=logging.DEBUG)`
- Use `make test-very-verbose` for detailed auth flow logs

### Additional Development Commands

**See full list of available targets:**
```bash
make help  # Complete list with descriptions
```

**Commonly used targets include:** `build`, `build-prod`, `build-claude-extension`, `clean-test`

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

## AI Assistant Guidelines

1. **Always reference [README.md](README.md)** first for basic project information
2. **Security**: Never commit credentials or sensitive data
3. **Testing**: Run `make test` after significant changes
4. **Code Style**: stick to the settings in `pyproject.toml` and `.editorconfig`
5. **Dependencies**: Check `pyproject.toml` for current dependencies

This guide supplements the README with development-specific information for AI coding assistants working on the Insights MCP project. The architecture supports multiple Red Hat Insights service toolsets through a unified server interface.
