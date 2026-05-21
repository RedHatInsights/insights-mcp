"""Single source of truth for image-builder LLM test prompts and example questions."""

from insights_mcp.test_prompts_data import PromptRegistry

TOOLSET_TITLE = "Image Builder MCP Test Prompts"

PROMPTS = PromptRegistry(
    rhel_initial_question="Can you create a RHEL 9 image for me?",
    image_build_status="What is the status of my latest image build?",
    llm_paging_1="List my latest 2 blueprints",
    llm_paging_2="Can you show me the next 3 blueprints?",
    list_image_types="Which image types are available?",
    complete_conversation_flow="Can you help me understand what blueprints are available?",
    list_recent_builds=(
        "List all my recent builds",
        ("image-builder__get_composes",),
        "Should use get_composes for build listings",
    ),
    what_blueprints=(
        "What blueprints do I have?",
        ("image-builder__get_blueprints",),
        "Should use get_blueprints for blueprint listings",
    ),
    show_blueprints=(
        "Please show my blueprints",
        ("image-builder__get_blueprints",),
        "Should use get_blueprints for blueprint listings",
    ),
)
