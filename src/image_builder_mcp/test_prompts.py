"""Single source of truth for image-builder LLM test prompts and example questions."""

from mcp_llm_eval.data import PromptRegistry, PromptWithTools

TOOLSET_TITLE = "Image Builder MCP Test Prompts"

PROMPTS = PromptRegistry(
    rhel_initial_question=PromptWithTools(
        turns=("Can you create a RHEL 9 image for me?",),
        expected_tools=(
            "image-builder__get_openapi",
            "image-builder__get_blueprints",
            "image-builder__get_distributions",
        ),
        turn_criteria=(
            "The LLM should NOT immediately call image-builder__create_blueprint. "
            "Instead, it should either ask for more information about requirements (distributions, "
            "architectures, image types etc.) or optionally use get_openapi to understand the system first. "
            "In any case the response should be targeted to the user for more information."
        ),
        forbidden_tools=("image-builder__create_blueprint",),
    ),
    image_build_status=PromptWithTools(
        turns=("What is the status of my latest image build?",),
        expected_tools=("image-builder__get_composes", "image-builder__get_compose_details"),
        turn_criteria=(
            "The response should contain the status of the latest image build, "
            "including details such as the compose ID, image type, or distribution."
        ),
    ),
    llm_paging=PromptWithTools(
        turns=(
            "List my latest 2 blueprints",
            "Can you show me the next 3 blueprints?",
        ),
        expected_tools=("image-builder__get_blueprints",),
        expected_args={
            "image-builder__get_blueprints": [
                {"limit": 2},  # No offset, because it's default and doesn't get caught without with kwargs
                {"limit": 3, "offset": 2},
            ]
        },
        assert_no_memory_overflow=True,
    ),
    list_image_types=PromptWithTools(
        turns=("Which image types are available?",),
        expected_tools=("image-builder__get_openapi",),
        turn_criteria=(
            "The response should list the available image types. "
            "The response must not contain edge-commit, edge-installer, rhel-edge-commit, "
            "rhel-edge-installer or report them as deprecated image types."
        ),
        forbidden_tools=("image-builder__create_blueprint",),
    ),
    complete_conversation_flow=PromptWithTools(
        turns=("Can you help me understand what blueprints are available?",),
        expected_tools=("image-builder__get_blueprints",),
        conversation_criteria=(
            "The conversation should demonstrate proper agent behavior:\n"
            "1. Understanding user intent\n"
            "2. Using appropriate tools to gather information or providing helpful and informative responses\n"
            "3. The 'content' of the conversation contains only json then this is considered a failure\n"
            "4. Take care that tool calls are properly part of a 'tool_call' object\n"
        ),
    ),
    list_recent_builds=PromptWithTools(
        turns=("List all my recent builds",),
        expected_tools=("image-builder__get_composes",),
    ),
    what_blueprints=PromptWithTools(
        turns=("What blueprints do I have?",),
        expected_tools=("image-builder__get_blueprints",),
    ),
    show_blueprints=PromptWithTools(
        turns=("Please show my blueprints",),
        expected_tools=("image-builder__get_blueprints",),
    ),
)
