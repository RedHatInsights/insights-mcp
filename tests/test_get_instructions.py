"""Test get_instructions for read-only vs all-tools modes."""

from insights_mcp.server import MCPS, get_instructions

ADDITIONAL_TOOLS_PHRASE = "Additional tools are available but not enabled"


def test_instructions_contain_additional_tools_phrase_in_readonly_mode() -> None:
    """In read-only mode, instructions must mention that additional tools exist but are not enabled."""
    allowed_mcps = [mcp.toolset_name for mcp in MCPS]
    instructions = get_instructions(allowed_mcps, readonly=True)
    assert ADDITIONAL_TOOLS_PHRASE in instructions, (
        f"Read-only mode instructions must contain '{ADDITIONAL_TOOLS_PHRASE}'"
    )


def test_instructions_omit_additional_tools_phrase_in_all_tools_mode() -> None:
    """In all-tools mode, instructions must not mention that additional tools are not enabled."""
    allowed_mcps = [mcp.toolset_name for mcp in MCPS]
    instructions = get_instructions(allowed_mcps, readonly=False)
    assert ADDITIONAL_TOOLS_PHRASE not in instructions, (
        f"All-tools mode instructions must not contain '{ADDITIONAL_TOOLS_PHRASE}'"
    )
