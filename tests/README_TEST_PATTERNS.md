# Test Pattern Framework

This document explains the test pattern framework implemented in this project to create reusable test functions across different MCP modules.

## Structure Overview

```
tests/
├── test_patterns.py           # Reusable test functions (patterns)
├── test_mcp_api.py            # Generic MCP server tests
└── conftest.py                # Common fixtures

src/
├── image_builder_mcp/tests/
│   ├── test_mcp_tool_validation.py  # Image-builder specific parametrized tests
│   └── conftest.py                  # Re-exports fixtures from top-level
└── [future_module]/tests/
    ├── test_mcp_tool_validation.py  # Module-specific parametrized tests
    └── conftest.py                  # Re-exports fixtures from top-level
```

## How It Works

### 1. Pattern Functions (`tests/test_patterns.py`)

Contains reusable test functions that accept parameters and perform common test operations:

```python
def assert_mcp_tool_descriptions_and_annotations(
    mcp_tools, subtests, tool_name: str, expected_desc: str, params: Dict[str, Dict[str, Any]]
):
    """Reusable test function to verify MCP tools include proper descriptions and annotations."""
    # Generic test logic here...
```

### 2. Module-Specific Tests (`src/[module]/tests/test_mcp_tool_validation.py`)

Import pattern functions and provide module-specific parameters:

```python
from tests.test_patterns import assert_mcp_tool_descriptions_and_annotations

@pytest.mark.parametrize(
    "tool_name, expected_desc, params",
    [
        ("module__get_items", "Get items from module", {"limit": {...}}),
        # More module-specific test cases...
    ],
)
def test_mcp_tools_include_descriptions_and_annotations(mcp_tools, subtests, tool_name, expected_desc, params):
    """Test that the module MCP tools include descriptions and annotations."""
    assert_mcp_tool_descriptions_and_annotations(mcp_tools, subtests, tool_name, expected_desc, params)
```

### 3. Fixture Inheritance (`src/[module]/tests/conftest.py`)

Each module's `conftest.py` re-exports fixtures from the top-level tests:

```python
from tests.conftest import (
    mcp_tools,
    mcp_server_url,
    # ... other fixtures
)
```

## Adding a New Module

1. Create `src/[new_module]/tests/conftest.py`:
   ```python
   from tests.conftest import (
       mcp_tools,
       mcp_server_url,
       # ... other needed fixtures
   )
   ```

2. Create `src/[new_module]/tests/test_mcp_tool_validation.py`:
   ```python
   from tests.test_patterns import assert_mcp_tool_descriptions_and_annotations

   @pytest.mark.parametrize(
       "tool_name, expected_desc, params",
       [
           # Your module-specific test parameters here
       ],
   )
   def test_mcp_tools_include_descriptions_and_annotations(mcp_tools, subtests, tool_name, expected_desc, params):
       assert_mcp_tool_descriptions_and_annotations(mcp_tools, subtests, tool_name, expected_desc, params)
   ```

3. Add any new pattern functions to `tests/test_patterns.py` if needed

## Example Use Cases

- **Tool validation**: Verify all tools have proper descriptions, parameters, and schemata
- **Transport testing**: Ensure all transport types (HTTP, SSE, stdio) work correctly
- **Integration testing**: Common patterns for testing tool execution and responses
- **Error handling**: Standardized error handling validation across modules

This framework scales well as you add more MCP modules to your project while maintaining consistency and reducing code duplication.
