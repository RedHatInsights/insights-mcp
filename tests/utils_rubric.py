"""Utility functions for rubric-kit based LLM evaluation tests."""

import asyncio
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial

import yaml
from rubric_kit.llm_judge import evaluate_rubric_with_panel
from rubric_kit.pdf_export import export_evaluation_pdf
from rubric_kit.processor import calculate_percentage_score, calculate_total_score, evaluate_rubric


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


def generate_report(
    results,
    rubric,
    panel_config,
    llm_config,
    total_score,
    max_score,
    percentage,
    chat_content,
    verbose_logger,
    reports_dir,
    report_title,
    test_prompt=None,
):
    """Generate PDF and YAML reports from evaluation results.

    Args:
        results: Evaluation results from rubric-kit
        rubric: The loaded rubric object
        panel_config: Judge panel configuration
        llm_config: LLM configuration dict with name/MODEL_ID
        total_score: Total score achieved
        max_score: Maximum possible score
        percentage: Score percentage
        chat_content: Formatted chat session content
        verbose_logger: Logger for output
        reports_dir: Path to directory for saving reports
        report_title: Title for the report
        test_prompt: Optional test prompt to include in metadata
    """
    # Create reports directory
    reports_dir.mkdir(exist_ok=True)

    # Generate timestamp and model name for unique filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_name = llm_config.get("name", "Unknown Model").replace(" ", "_").replace("/", "-")

    # Build self-contained output structure (same format as rubric-kit CLI)
    output_data = {
        "results": results,
        "summary": {"total_score": total_score, "max_score": max_score, "percentage": round(percentage, 1)},
        "rubric": {
            "dimensions": [
                {
                    "name": dim.name,
                    "description": dim.description,
                    "grading_type": dim.grading_type,
                    "scores": dim.scores,
                    "pass_above": dim.pass_above,
                }
                for dim in rubric.dimensions
            ],
            "criteria": [
                {
                    "name": crit.name,
                    "category": crit.category,
                    "dimension": crit.dimension,
                    "criterion": crit.criterion,
                    "weight": crit.weight,
                }
                for crit in rubric.criteria
            ],
        },
        "judge_panel": {
            "judges": [
                {
                    "name": j.name,
                    "model": j.model,
                    "base_url": j.base_url,
                }
                for j in panel_config.judges
            ],
            "execution": {
                "mode": panel_config.execution.mode,
            },
            "consensus": {
                "mode": panel_config.consensus.mode,
            },
        },
        "input": {"type": "chat_session", "content": chat_content},
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "report_title": report_title,
            "test_prompt": test_prompt,
            "model_config": {
                "name": llm_config.get("name"),
                "model_id": llm_config.get("MODEL_ID"),
            },
        },
    }

    # Write YAML file (source of truth)
    yaml_path = reports_dir / f"evaluation_{model_name}_{timestamp}.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(output_data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
    verbose_logger.info("📄 YAML report saved to: %s", yaml_path)

    # Generate PDF report
    pdf_path = reports_dir / f"evaluation_{model_name}_{timestamp}.pdf"
    try:
        export_evaluation_pdf(str(yaml_path), str(pdf_path))
        verbose_logger.info("📊 PDF report saved to: %s", pdf_path)
    except Exception as e:
        verbose_logger.warning("⚠️ PDF generation failed: %s", e)


async def prompt_test_agent(test_agent, prompt, verbose_logger, chat_history=None):
    """Execute a prompt with the test agent and return the response and tools executed."""
    if chat_history is None:
        chat_history = []

    response, _, tools_executed, _ = await test_agent.execute_with_reasoning(prompt, chat_history=chat_history)
    verbose_logger.info("Response received: %s", response[:200] + "..." if len(response) > 200 else response)
    verbose_logger.info("Tools invoked: %s", tools_executed)
    return response, tools_executed


def _save_chat_session(chat_content, verbose_logger):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(chat_content)
        chat_session_file = f.name
    verbose_logger.info("Chat session saved to: %s", chat_session_file)
    return chat_session_file


async def evaluate_with_rubric(rubric, chat_content, panel_config, verbose_logger):
    """Evaluate chat content against a rubric using a judge panel.

    Runs rubric-kit evaluation in a thread pool to avoid asyncio conflicts,
    then processes and logs the results.

    Args:
        rubric: Loaded rubric object with dimensions and criteria.
        chat_content: Formatted chat session string to evaluate.
        panel_config: Judge panel configuration with judges and consensus settings.
        verbose_logger: Logger for progress and result output.

    Returns:
        Tuple of (results, total_score, max_score, percentage).
    """
    verbose_logger.info("Loaded rubric with %d dimensions, %d criteria", len(rubric.dimensions), len(rubric.criteria))
    verbose_logger.info("Loaded judge panel with %d judges", len(panel_config.judges))

    try:
        # Write chat session to temporary file for evaluation
        chat_session_file = _save_chat_session(chat_content, verbose_logger)

        # Evaluate using rubric-kit judge panel
        # Run in thread pool to avoid asyncio.run() conflict (rubric-kit uses asyncio.run internally)
        verbose_logger.info("Evaluating with judge panel...")
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            evaluations = await loop.run_in_executor(
                executor, partial(evaluate_rubric_with_panel, rubric, chat_session_file, panel_config)
            )
    finally:
        os.unlink(chat_session_file)

    # Process scores
    results = evaluate_rubric(rubric, evaluations)
    total_score, max_score = calculate_total_score(results)
    percentage = calculate_percentage_score(results)

    verbose_logger.info("📊 Evaluation complete: %d/%d (%.1f%%)", total_score, max_score, percentage)

    # Log individual criterion results
    for result in results:
        status = "✅" if result["result"] == "pass" else "❌"
        verbose_logger.info(
            "%s %s: %s (score: %d/%d)",
            status,
            result["criterion_name"],
            result["result"],
            result["score"],
            result["max_score"],
        )
        if result.get("reason"):
            verbose_logger.info("   Reason: %s", result["reason"])

    return results, total_score, max_score, percentage


def check_passing_threshold(results, percentage: float, passing_threshold: float):
    """Check if the evaluation results pass the passing threshold."""
    assert percentage >= passing_threshold, (
        f"Evaluation score {percentage:.1f}% is below passing threshold {passing_threshold}%. Results: {results}"
    )


def check_tool_correctness(results, expected_tool: str):
    """Check if the evaluation results pass the tool correctness threshold."""
    tool_result = next((r for r in results if r["criterion_name"] == "tool_correctness"), None)
    assert tool_result is not None, "Tool correctness criterion not found in results"
    assert tool_result["result"] == "pass", (
        f"Expected {expected_tool} to be called. Tool breakdown: {tool_result.get('tool_breakdown', 'N/A')}"
    )
