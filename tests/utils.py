"""Utility functions for testing."""

import json
import logging
import multiprocessing
import os
import socket
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests
from llama_index.core.llms import ChatMessage

from instrumentation_tests.mcp_jsonrpc import DEFAULT_JSON_HEADERS, create_mcp_init_request


def should_skip_llm_tests() -> bool:
    """Check if LLM integration tests should be skipped."""
    required_vars = ["MODEL_API", "MODEL_ID", "USER_KEY"]
    return not all(os.getenv(var) for var in required_vars)


def load_llm_configurations() -> Tuple[List[Dict[str, Optional[str]]], Optional[Dict[str, str]]]:
    """Load LLM configurations from test_config.json file."""
    config_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_config.json")

    if not os.path.exists(config_file):
        # Fallback to environment variables for backward compatibility
        if not should_skip_llm_tests():
            return [
                {
                    "name": "Default Model",
                    "MODEL_API": os.getenv("MODEL_API"),
                    "MODEL_ID": os.getenv("MODEL_ID"),
                    "USER_KEY": os.getenv("USER_KEY"),
                }
            ], None
        return [], None

    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        configurations = []
        for llm_config in config.get("llm_configurations", []):
            # Substitute environment variables in configuration
            resolved_config: Dict[str, Optional[str]] = {}
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
        guardian_llm: Optional[Dict[str, str]] = config.get("guardian_llm")
        return configurations, guardian_llm

    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        logging.warning("Error loading test_config.json: %s. Falling back to environment variables.", e)
        # Fallback to environment variables
        if not should_skip_llm_tests():
            return [
                {
                    "name": "Default Model",
                    "MODEL_API": os.getenv("MODEL_API"),
                    "MODEL_ID": os.getenv("MODEL_ID"),
                    "USER_KEY": os.getenv("USER_KEY"),
                }
            ], None
        return [], None


def should_skip_llm_matrix_tests() -> bool:
    """Check if LLM matrix tests should be skipped."""
    configurations, _ = load_llm_configurations()
    return len(configurations) == 0


def cleanup_server_process(server_process: multiprocessing.Process) -> None:
    """Helper function to properly cleanup a server process."""
    if server_process.is_alive():
        server_process.terminate()
        server_process.join(timeout=5)
        if server_process.is_alive():
            server_process.kill()


class ServerStartupError(Exception):
    """Exception raised when MCP server fails to start."""


class ServerConnectionError(Exception):
    """Exception raised when unable to connect to MCP server."""


def get_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def get_server_url_and_port(transport: str) -> tuple[str, int]:
    """Get server URL and port for the given transport type."""
    port = get_free_port()

    if transport == "stdio":
        # For stdio, we don't need a URL/port, but we'll use a placeholder
        server_url = "stdio"
    elif transport == "sse":
        server_url = f"http://127.0.0.1:{port}/sse"
    else:  # http
        server_url = f"http://127.0.0.1:{port}/mcp/"
    return server_url, port


def _resolve_container_brand(container_brand: str | None) -> str:
    """Return the container brand to use when starting a test server subprocess."""
    return container_brand if container_brand is not None else os.getenv("CONTAINER_BRAND", "insights")


@dataclass(frozen=True)
class _ServerWorkerConfig:
    """Arguments for :func:`_server_worker` (pickled for multiprocessing)."""

    transport: str
    port: int
    toolset: str | None
    readonly: bool
    container_brand: str


def _server_worker(config: _ServerWorkerConfig, server_queue: multiprocessing.Queue) -> None:
    """Start the MCP server in a separate process.

    This function is at module level so it can be pickled for multiprocessing.
    ``container_brand`` is passed explicitly so tests work when the default
    multiprocessing start method is ``forkserver`` (Python 3.14+), which does not
    pick up ``os.environ`` changes made after the forkserver process starts.
    """
    try:
        os.environ["CONTAINER_BRAND"] = config.container_brand

        # Mock sys.argv to simulate command line arguments
        original_argv = sys.argv.copy()
        try:
            base_args = ["insights_mcp"]

            # Add toolset argument if specified
            if config.toolset is not None:
                base_args.extend(["--toolset", config.toolset])

            # Add all-tools argument when full access is requested (default is read-only)
            if not config.readonly:
                base_args.append("--all-tools")

            # Add transport-specific arguments
            if config.transport == "stdio":
                base_args.append("stdio")
            elif config.transport == "sse":
                base_args.extend(["sse", "--host", "127.0.0.1", "--port", str(config.port)])
            else:  # http
                base_args.extend(["http", "--host", "127.0.0.1", "--port", str(config.port)])

            sys.argv = base_args

            # Import and call main
            # pylint: disable=import-outside-toplevel
            from insights_mcp.server import main

            # Signal that server is starting
            server_queue.put("starting")

            # Start the server
            main()

        finally:
            sys.argv = original_argv

    except Exception as e:  # pylint: disable=broad-exception-caught
        server_queue.put(f"error: {e}")


def _wait_for_http_server_ready(
    server_url: str,
    server_process: multiprocessing.Process,
    port: int,
    *,
    max_retries: int = 5,
) -> None:
    """Confirm the HTTP MCP server accepts an initialize request."""
    if not server_process.is_alive():
        raise ServerStartupError(
            f"Server process died before init request connection to host {server_url}."
            f"Process exit code: {server_process.exitcode}"
        )

    for attempt in range(max_retries):
        try:
            test_request = create_mcp_init_request()
            response = requests.post(server_url, json=test_request, headers=DEFAULT_JSON_HEADERS, timeout=10)

            if response.status_code == 200:
                return

            if attempt == max_retries - 1:
                raise ServerConnectionError(
                    (
                        f"Server not responding properly after {max_retries} "
                        f"attempts: {response.status_code} - {response.text}. "
                        f"Server process: {'alive' if server_process.is_alive() else 'dead'}"
                    )
                )

            time.sleep(2)

        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise ServerConnectionError(
                    f"Failed to connect to server after {max_retries} attempts. "
                    f"Server process: {'alive' if server_process.is_alive() else 'dead'}, "
                    f"Port: {port}, URL: {server_url}, Error: {e}"
                ) from e
            time.sleep(2)


def start_insights_mcp_server(
    transport: str,
    timeout: int = 30,
    toolset: str | None = None,
    readonly: bool = False,
    container_brand: str | None = None,
) -> tuple[str, multiprocessing.Process]:
    """Start the insights MCP server with specified transport type.

    Args:
        transport: Transport type ('http', 'sse', or 'stdio')
        timeout: Timeout in seconds for server startup
        toolset: Toolset to use (e.g., 'all', 'image-builder', 'inventory', 'image-builder,inventory')
        readonly: If True, only register read-only tools
        container_brand: Brand passed to the server process (defaults to ``CONTAINER_BRAND`` env or ``insights``)

    Returns:
        Tuple of (server_url, server_process)
    """
    server_url, port = get_server_url_and_port(transport)
    worker_config = _ServerWorkerConfig(
        transport=transport,
        port=port,
        toolset=toolset,
        readonly=readonly,
        container_brand=_resolve_container_brand(container_brand),
    )
    server_queue: multiprocessing.Queue = multiprocessing.Queue()

    # Start server process using module-level function for pickling compatibility
    server_process = multiprocessing.Process(
        target=_server_worker,
        args=(worker_config, server_queue),
        daemon=True,
    )
    server_process.start()

    try:
        # Wait for server to start
        start_signal = server_queue.get(timeout=timeout)
        if start_signal.startswith("error:"):
            raise RuntimeError(f"Server failed to start: {start_signal}")

        # Additional wait for server to be fully ready
        time.sleep(3)

        if transport == "http":
            _wait_for_http_server_ready(server_url, server_process, port)
        # For SSE transport, skip connectivity test since SSE streams continuously.

        return server_url, server_process

    except Exception:  # pylint: disable=broad-exception-caught
        cleanup_server_process(server_process)
        raise


def pretty_print_chat_history(
    conversation_history: List[ChatMessage], llm_name: str, verbose_logger: logging.Logger
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
