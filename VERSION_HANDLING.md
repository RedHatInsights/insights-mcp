# Version Handling for `insights-mcp`

## Overview
The user agent string `insights-mcp/{version}` is dynamically set based on the package version, with support for environment variable overrides during container builds.

## Implementation

### 1. Version Detection Order
1. **Environment Variable**: `INSIGHTS_MCP_VERSION` (highest priority)
2. **Package Metadata**: From installed package via `importlib.metadata`
3. **Fallback**: `0.0.0-dev` for development environments

### 2. User Agent String
- Format: `insights-mcp/{version}` (follows standard HTTP User-Agent conventions)
- Dynamically constructed in `src/insights_mcp/client.py`
- Imports version from `src/insights_mcp/__init__.py`

### 3. Build Systems Compatibility

#### Local Builds (Makefile)
```bash
# Extracts version from pyproject.toml
make build  # Uses version 0.0.0
# Or with custom tag
TAG=1.2.3 make build  # Uses version 1.2.3
```

#### GitHub Actions
- Generates dynamic tags: `YYYYMMDD-HHMMSS-{SHA}`
- Passes version via `--build-arg INSIGHTS_MCP_VERSION` to container builds
- Example: `insights-mcp/20250118-103000-abc12345`

#### Tekton Pipelines
- Uses git revision as container tag
- Falls back to package metadata version (0.1.0)
- Container image tags: `insights-mcp:on-pr-{revision}` or `insights-mcp:{revision}`

#### Containerfile
- Accepts optional `INSIGHTS_MCP_VERSION` build argument
- Sets as environment variable in runtime stage
- Falls back to package metadata if not provided

## Testing

### Local Python
```bash
# Default version
python -c "from src.insights_mcp import __version__; print(__version__)"
# Output: 0.0.0

# With environment override
INSIGHTS_MCP_VERSION="1.2.3" python -c "from src.insights_mcp import __version__; print(__version__)"
# Output: 1.2.3
```

### Container Builds
```bash
# With specific version
podman build --build-arg INSIGHTS_MCP_VERSION=1.2.3 -t insights-mcp .

# Using Makefile (auto-detects from pyproject.toml)
make build
```
