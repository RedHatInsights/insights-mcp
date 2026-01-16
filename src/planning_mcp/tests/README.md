# Planning MCP Server tests

This MCP server provides tools to access Red Hat Insights Planning data for RHEL Lifecycle and roadmap management.

## Development

### Dependencies

Theses tests have optional test dependencies that are not required for general development:

- **rubric-kit** - Used for specialized LLM testing with the rubric-kit framework. See the Rubric tests [README.md](.rubic/README.md) for more information.

### Installing Optional Dependencies

To install the planning-specific test dependencies:

```bash
# Install only planning dependencies
uv sync --extra planning

# Install both dev and planning dependencies
uv sync --extra dev --extra planning

# Install all optional dependencies
uv sync --all-extras
```

### Running Tests

Standard tests can be run without the `planning` extra:

```bash
# Run all planning tests
uv run pytest src/planning_mcp/tests/

# Run specific test file
uv run pytest src/planning_mcp/tests/test_upcoming.py
```

Tests that require `rubric-kit` are located in:
- `src/planning_mcp/tests/rubric-kit/` - Requires the `planning` extra to be installed

## Authentication

This server uses the shared Insights authentication infrastructure. See the main [README.md](/README.md) for authentication setup instructions.
