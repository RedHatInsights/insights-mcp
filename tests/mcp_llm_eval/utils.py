"""Shared configuration and logging helpers for MCP LLM tests."""

import json
import logging
import os

from deepeval.models import GPTModel
from llama_index.core.llms import ChatMessage


def should_skip_llm_tests() -> bool:
    """Check if LLM integration tests should be skipped."""
    required_vars = ["MODEL_API", "MODEL_ID", "USER_KEY"]
    return not all(os.getenv(var) for var in required_vars)


def should_skip_llm_matrix_tests() -> bool:
    """Check if LLM matrix tests should be skipped."""
    configurations, _ = load_llm_configurations()
    return len(configurations) == 0


def _get_llm_config_from_env() -> list[dict[str, str | None]]:
    return [
        {
            "name": "Default Model",
            "MODEL_API": os.getenv("MODEL_API"),
            "MODEL_ID": os.getenv("MODEL_ID"),
            "USER_KEY": os.getenv("USER_KEY"),
        }
    ]


def load_llm_configurations() -> tuple[list[dict[str, str | None]], dict[str, str] | None]:
    """Load LLM configurations from test_config.json file."""
    config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "test_config.json")

    if not os.path.exists(config_file):
        # Fallback to environment variables for backward compatibility
        if not should_skip_llm_tests():
            return _get_llm_config_from_env(), None
        return [], None

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        configurations = []
        for llm_config in config.get("llm_configurations", []):
            # Substitute environment variables in configuration
            resolved_config: dict[str, str | None] = {}
            for key, value in llm_config.items():
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    env_var = value[2:-1]  # Remove ${ and }
                    resolved_value = os.getenv(env_var)
                    if resolved_value:
                        resolved_config[key] = resolved_value
                    else:
                        # Skip this configuration if required env var is missing
                        break
                else:
                    resolved_config[key] = value

            # Only add configuration if all required variables are present
            if all(key in resolved_config and resolved_config[key] for key in ["MODEL_API", "MODEL_ID", "USER_KEY"]):
                configurations.append(resolved_config)
        guardian_llm: dict[str, str] | None = config.get("guardian_llm")
        return configurations, guardian_llm

    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        logging.warning("Error loading test_config.json: %s. Falling back to environment variables.", e)
        # Fallback to environment variables
        if not should_skip_llm_tests():
            return _get_llm_config_from_env(), None
        return [], None


def gpt_model_from_config(config: dict[str, str]) -> GPTModel:
    """Build deepeval GPTModel for OpenAI-compatible endpoints from test config."""
    return GPTModel(
        model=config["MODEL_ID"],
        base_url=config["MODEL_API"],
        api_key=config["USER_KEY"],
        temperature=0,
    )


def pretty_print_chat_history(
    conversation_history: list[ChatMessage], llm_name: str, verbose_logger: logging.Logger
) -> None:
    """Pretty print chat history for debugging."""
    verbose_logger.info("Full conversation history:")

    if len(conversation_history) == 0:
        verbose_logger.info("No conversation history")
        return

    for i, turn in enumerate(conversation_history):
        if turn.role == "user":
            verbose_logger.info(f"{llm_name} turn {i + 1}: 👤 User: {turn.content}")
        elif turn.role == "assistant":
            verbose_logger.info(f"{llm_name} turn {i + 1}: 🤖 Assistant: {turn.content}")
        elif turn.role == "tool":
            verbose_logger.info(f"{llm_name} turn {i + 1}: 🔧 Tool: {turn.content}")
        else:
            verbose_logger.info(f"{llm_name} turn {i + 1}: ? {turn.role}: {turn.content}")
