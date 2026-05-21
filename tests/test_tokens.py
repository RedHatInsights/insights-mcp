"""Test MCP tool definition input token counts against configured LLM encodings."""

import os

import pytest

from insights_mcp.tool_tokens import all_tools_mode, build_catalog_rows, resolve_encoding
from tests.utils import load_llm_configurations, should_skip_llm_matrix_tests

llm_configurations, _ = load_llm_configurations()

DEFAULT_MAX_TOOL_INPUT_TOKENS = 15000


def _max_tool_input_tokens() -> int:
    raw = os.getenv("INSIGHTS_MCP_MAX_TOOL_INPUT_TOKENS", str(DEFAULT_MAX_TOOL_INPUT_TOKENS))
    return int(raw)


@pytest.mark.skipif(should_skip_llm_matrix_tests(), reason="No valid LLM configurations found")
class TestToolInputTokens:
    """Assert all-tools MCP catalog fits within the configured input token budget."""

    @pytest.mark.parametrize("llm_config", llm_configurations, ids=[config["name"] for config in llm_configurations])
    def test_all_tools_input_tokens(self, llm_config):
        """All-tools catalog token count must not exceed INSIGHTS_MCP_MAX_TOOL_INPUT_TOKENS."""
        model_id = llm_config["MODEL_ID"]
        encoding = resolve_encoding(model_id, llm_config)
        rows = build_catalog_rows([all_tools_mode()], encoding)
        row = rows[0]
        limit = _max_tool_input_tokens()

        assert row.token_count <= limit, (
            f"Tool input tokens for {llm_config['name']} ({model_id}): got {row.token_count}, "
            f"want <= {limit} ({row.tool_count} tools, encoding {encoding.name})"
        )
