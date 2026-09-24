"""Tests for MkDocs staging link rewrites."""

from prepare_mkdocs import patch_for_mkdocs


def test_patch_for_mkdocs_rewrites_mcp_llm_eval_readme_link() -> None:
    patched = patch_for_mkdocs("See [`tests/mcp_llm_eval/README.md`](tests/mcp_llm_eval/README.md).")
    assert patched == "See [`tests/mcp_llm_eval/README.md`](mcp-llm-eval.md)."
