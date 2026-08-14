"""Single source of truth for image-builder LLM test prompts and example questions."""

from insights_mcp.test_prompts_data import PromptRegistry, PromptWithTools

TOOLSET_TITLE = "Image Builder MCP Test Prompts"

PROMPTS = PromptRegistry(
    rhel_initial_question=PromptWithTools(
        turns=("Can you create a RHEL 9 image for me?",),
        expected_tools=(
            "image-builder__get_openapi",
            "image-builder__get_blueprints",
            "image-builder__get_distributions",
        ),
        guardian_criteria=(
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
        guardian_criteria=(
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
    ),
    list_image_types=PromptWithTools(
        turns=("Which image types are available?",),
        expected_tools=("image-builder__get_openapi",),
        guardian_criteria=(
            "The response should list the available image types. "
            "The response must not contain edge-commit, edge-installer, rhel-edge-commit, "
            "rhel-edge-installer or report them as deprecated image types."
        ),
        forbidden_tools=("image-builder__create_blueprint",),
    ),
    complete_conversation_flow=PromptWithTools(
        turns=("Can you help me understand what blueprints are available?",),
        expected_tools=("image-builder__get_blueprints",),
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
