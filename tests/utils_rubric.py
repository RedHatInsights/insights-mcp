"""Utility functions for rubric-kit based LLM evaluation tests."""

from datetime import datetime

import yaml


def format_chat_session(user_prompt: str, response: str, tools_executed: list) -> str:
    """Format a chat session for rubric-kit evaluation.

    Rubric-kit expects MCP format for parsing tool calls from chat sessions:
    - `### User:` for user messages
    - `### Assistant:` for assistant responses
    - `#### Tool Call:` for tool invocations
    """
    lines = []

    # User message
    lines.append("### User:")
    lines.append(user_prompt)
    lines.append("")

    # Assistant response with tool calls in MCP format
    lines.append("### Assistant:")

    # Tool calls (if any) in MCP format
    if tools_executed:
        for tool in tools_executed:
            # Handle both ToolCall objects and dicts
            if hasattr(tool, "name"):
                tool_name = tool.name
                params = getattr(tool, "input_parameters", {}) or {}
            elif isinstance(tool, dict):
                tool_name = tool.get("name", str(tool))
                params = tool.get("input_parameters", {})
            else:
                tool_name = str(tool)
                params = {}

            lines.append(f"#### Tool Call: `{tool_name}`")
            lines.append("**Arguments:**")
            if params:
                for k, v in params.items():
                    lines.append(f"* **{k}**: {v}")
            else:
                lines.append("*empty object*")
            lines.append("")
            lines.append("#### Tool Response:")
            lines.append("[Tool executed successfully]")
            lines.append("")

    # Final response
    lines.append(response)

    return "\n".join(lines)


def generate_report_folder(report_title, llm_config, reports_dir):
    """Generate a report folder for the report."""
    # Generate timestamp and model name for folder naming
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = llm_config.get("name", "Unknown Model").replace(" ", "_").replace("/", "-")
    # Create timestamped report folder
    report_folder = reports_dir / f"{timestamp}_{report_title.replace(' ', '_')}_{model_name}"
    report_folder.mkdir(parents=True, exist_ok=True)
    return report_folder


def parse_results_summary(results_path):
    """Parse rubric-kit results YAML and return summary metrics."""
    with open(results_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    summary = data.get("summary")
    if not summary:
        raise ValueError(f"Missing summary section in {results_path}")

    total_score = summary.get("total_score")
    max_score = summary.get("max_score")
    percentage = summary.get("percentage")

    if total_score is None or max_score is None or percentage is None:
        raise ValueError(f"Incomplete summary in {results_path}: {summary}")

    return {
        "total_score": float(total_score),
        "max_score": float(max_score),
        "percentage": float(percentage),
    }


def check_results_threshold(results_path, passing_threshold):
    """Check if results YAML meets the passing threshold."""
    summary = parse_results_summary(results_path)
    percentage = summary["percentage"]
    assert percentage >= passing_threshold, (
        f"Evaluation score {percentage:.1f}% is below passing threshold {passing_threshold}%. Summary: {summary}"
    )


async def prompt_test_agent(test_agent, prompt, verbose_logger, chat_history=None):
    """Execute a prompt with the test agent and return the response and tools executed."""
    if chat_history is None:
        chat_history = []

    response, _, tools_executed, _ = await test_agent.execute_with_reasoning(prompt, chat_history=chat_history)
    verbose_logger.debug("Response received: %s", response[:200] + "..." if len(response) > 200 else response)
    verbose_logger.debug("Tools invoked: %s", tools_executed)
    return response, tools_executed


def check_passing_threshold(results_path, passing_threshold: float):
    """Check if the evaluation results pass the passing threshold."""
    summary = parse_results_summary(results_path)
    assert summary["percentage"] >= passing_threshold, (
        f"Evaluation score {summary['percentage']:.1f}% is below passing threshold {passing_threshold}%."
        f"Results: {summary}"
    )


def check_tool_correctness(results, expected_tool: str):
    """Check if the evaluation results pass the tool correctness threshold."""
    tool_results = [r for r in results if r.name == expected_tool]
    if len(tool_results) != 1:
        raise AssertionError(f"Expected {expected_tool} to be called exactly once, but got {len(tool_results)}")


def check_tool_input_parameters(tools_executed, expected_tool_input_parameters: dict | None):
    """Check if the tool input parameters are correct."""
    expected_tool_input_parameters = expected_tool_input_parameters or {}
    # If there are no tool_input_parameters, it will fail at the assertion below so no need to check for None
    try:
        tool_input_parameters = tools_executed[0].input_parameters
    except IndexError:
        tool_input_parameters = {}

    if tool_input_parameters and not expected_tool_input_parameters:
        raise AssertionError(f"Expected no tool input parameters, but got: {tool_input_parameters}")

    # If we expect tool input parameters, check if they are correct
    assert tool_input_parameters == expected_tool_input_parameters, (
        f"Expected tool input parameters: {expected_tool_input_parameters}, but got: {tool_input_parameters}"
    )
