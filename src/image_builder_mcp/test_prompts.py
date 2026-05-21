"""Single source of truth for image-builder LLM test prompts and example questions."""

from insights_mcp.test_prompts_data import PromptRegistry, PromptWithTools

TOOLSET_TITLE = "Image Builder MCP Test Prompts"

PROMPTS = PromptRegistry(
    rhel_initial_question=(
        "Can you create a RHEL 9 image for me?",
        ("image-builder__get_openapi", "image-builder__get_blueprints"),
    ),
    image_build_status=(
        "What is the status of my latest image build?",
        ("image-builder__get_composes", "image-builder__get_compose_details"),
    ),
    llm_paging=PromptWithTools(
        turns=(
            "List my latest 2 blueprints",
            "Can you show me the next 3 blueprints?",
        ),
        expected_tools=("image-builder__get_blueprints",),
    ),
    list_image_types=(
        "Which image types are available?",
        ("image-builder__get_openapi",),
    ),
    complete_conversation_flow=(
        "Can you help me understand what blueprints are available?",
        ("image-builder__get_blueprints",),
    ),
    list_recent_builds=(
        "List all my recent builds",
        ("image-builder__get_composes",),
    ),
    what_blueprints=(
        "What blueprints do I have?",
        ("image-builder__get_blueprints",),
    ),
    show_blueprints=(
        "Please show my blueprints",
        ("image-builder__get_blueprints",),
    ),
)
