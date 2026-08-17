"""Start Insights MCP server in a subprocess for tooling and tests."""

import multiprocessing
import os
import socket
import sys
import time
from dataclasses import dataclass

import requests

# HTTP MCP init probe (same contract as mcp_llm_eval.mcp_jsonrpc).
_MCP_JSON_HEADERS = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}


def _create_mcp_init_request() -> dict:
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"},
        },
    }


def cleanup_server_process(server_process: multiprocessing.Process) -> None:
    """Terminate and join an MCP server subprocess."""
    if not server_process.is_alive():
        return

    server_process.terminate()
    server_process.join(timeout=5)
    if not server_process.is_alive():
        return

    server_process.kill()
    server_process.join(timeout=5)


class ServerStartupError(Exception):
    """Raised when the MCP server fails to start."""


class ServerConnectionError(Exception):
    """Raised when unable to connect to the MCP server."""


def get_free_port() -> int:
    """Find a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("", 0))
        sock.listen(1)
        port = sock.getsockname()[1]
    return port


def get_server_url_and_port(transport: str) -> tuple[str, int]:
    """Return server URL and port for the given transport type."""
    port = get_free_port()

    if transport == "stdio":
        server_url = "stdio"
    elif transport == "sse":
        server_url = f"http://127.0.0.1:{port}/sse"
    else:
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
    """Start the MCP server in a separate process (picklable entry point).

    ``container_brand`` is passed explicitly so tests work when the default
    multiprocessing start method is ``forkserver`` (Python 3.14+), which does not
    pick up ``os.environ`` changes made after the forkserver process starts.
    """
    try:
        os.environ["CONTAINER_BRAND"] = config.container_brand

        original_argv = sys.argv.copy()
        try:
            base_args = ["insights_mcp"]

            if config.toolset is not None:
                base_args.extend(["--toolset", config.toolset])

            if not config.readonly:
                base_args.append("--all-tools")

            if config.transport == "stdio":
                base_args.append("stdio")
            elif config.transport == "sse":
                base_args.extend(["sse", "--host", "127.0.0.1", "--port", str(config.port)])
            else:
                base_args.extend(["http", "--host", "127.0.0.1", "--port", str(config.port)])

            sys.argv = base_args

            # pylint: disable=import-outside-toplevel
            from insights_mcp.server import main

            server_queue.put("starting")
            main()

        finally:
            sys.argv = original_argv

    except Exception as exc:  # pylint: disable=broad-exception-caught
        server_queue.put(f"error: {exc}")


def start_insights_mcp_server(
    transport: str,
    timeout: int = 30,
    toolset: str | None = None,
    readonly: bool = False,
    container_brand: str | None = None,
) -> tuple[str, multiprocessing.Process]:
    """Start the Insights MCP server and return its URL and process handle."""
    server_url, port = get_server_url_and_port(transport)
    worker_config = _ServerWorkerConfig(
        transport=transport,
        port=port,
        toolset=toolset,
        readonly=readonly,
        container_brand=_resolve_container_brand(container_brand),
    )

    server_queue: multiprocessing.Queue = multiprocessing.Queue()

    server_process = multiprocessing.Process(
        target=_server_worker,
        args=(worker_config, server_queue),
        daemon=True,
    )
    server_process.start()

    try:
        start_signal = server_queue.get(timeout=timeout)
        if start_signal.startswith("error:"):
            raise RuntimeError(f"Server failed to start: {start_signal}")

        time.sleep(3)

        if transport == "http":
            if not server_process.is_alive():
                raise ServerStartupError(
                    f"Server process died before init request to {server_url}. exit code: {server_process.exitcode}"
                )

            max_retries = 5
            for attempt in range(max_retries):
                try:
                    test_request = _create_mcp_init_request()
                    response = requests.post(server_url, json=test_request, headers=_MCP_JSON_HEADERS, timeout=10)

                    if response.status_code == 200:
                        break

                    if attempt == max_retries - 1:
                        raise ServerConnectionError(
                            f"Server not responding after {max_retries} attempts: "
                            f"{response.status_code} - {response.text}. "
                            f"process alive: {server_process.is_alive()}"
                        )

                    time.sleep(2)

                except requests.exceptions.RequestException as exc:
                    if attempt == max_retries - 1:
                        raise ServerConnectionError(
                            f"Failed to connect after {max_retries} attempts. "
                            f"URL: {server_url}, port: {port}, error: {exc}"
                        ) from exc
                    time.sleep(2)

        return server_url, server_process

    except Exception:
        cleanup_server_process(server_process)
        raise
