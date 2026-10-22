"""Local HTTP server adapter for the reusable Insights API mock."""

from __future__ import annotations

import json
from http import HTTPMethod
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from types import TracebackType
from typing import Any, cast
from urllib.parse import parse_qsl, urlsplit

from tests.mock_insights_api.registry import MockInsightsAPI, UnknownRouteError
from tests.mock_insights_api.types import MockRequest, MockResponse


class _MockHTTPServer(ThreadingHTTPServer):
    mock_api: MockInsightsAPI


class _MockRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # pylint: disable=invalid-name  # Required BaseHTTPRequestHandler hook.
        """Handle a GET request."""
        self._handle_request()

    def do_POST(self) -> None:  # pylint: disable=invalid-name  # Required BaseHTTPRequestHandler hook.
        """Handle a POST request."""
        self._handle_request()

    def do_PUT(self) -> None:  # pylint: disable=invalid-name  # Required BaseHTTPRequestHandler hook.
        """Handle a PUT request."""
        self._handle_request()

    def log_message(self, format: str, *args: Any) -> None:  # pylint: disable=redefined-builtin
        """Keep mock server requests out of test output."""

    def _handle_request(self) -> None:
        server = cast(_MockHTTPServer, self.server)
        try:
            response = server.mock_api.resolve(self._request())
        except UnknownRouteError as error:
            self._send_response(MockResponse(body=str(error), status=404))
            return
        except Exception as error:  # pylint: disable=broad-exception-caught
            self._send_response(MockResponse(body=str(error), status=500))
            return

        if response.error is not None:
            status = response.status if response.status >= 400 else 500
            self._send_response(MockResponse(body=str(response.error), status=status, headers=response.headers))
            return

        self._send_response(response)

    def _request(self) -> MockRequest:
        parsed_path = urlsplit(self.path)
        return MockRequest(
            method=HTTPMethod(self.command),
            path=parsed_path.path.removeprefix("/"),
            query=dict(parse_qsl(parsed_path.query, keep_blank_values=True)),
            body=self._request_body(),
        )

    def _request_body(self) -> Any:
        content_length = self.headers.get("Content-Length")
        if content_length is None:
            return None

        body = self.rfile.read(int(content_length))
        return json.loads(body) if body else None

    def _send_response(self, response: MockResponse) -> None:
        body = self._serialize_body(response.body)
        headers = dict(response.headers)
        headers["Content-Length"] = str(len(body))
        self.send_response(response.status)
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _serialize_body(body: Any) -> bytes:
        if body is None:
            return b""
        if isinstance(body, str):
            return body.encode("utf-8")
        return json.dumps(body).encode("utf-8")


class MockInsightsHTTPServer:
    """Serve the route registry over localhost for process-level tests."""

    def __init__(self, api: MockInsightsAPI, *, host: str = "127.0.0.1", port: int = 0) -> None:
        self.api = api
        self.host = host
        self.port = port
        self._server: _MockHTTPServer | None = None
        self._thread: Thread | None = None

    @property
    def base_url(self) -> str:
        """Return the URL to use as an ``InsightsClient`` base URL."""
        if self._server is None:
            raise RuntimeError("MockInsightsHTTPServer has not been started")
        address = cast(tuple[str, int], self._server.server_address)
        return f"http://{address[0]}:{address[1]}"

    def start(self) -> None:
        """Start serving requests in a daemon thread."""
        if self._server is not None:
            return

        server = _MockHTTPServer((self.host, self.port), _MockRequestHandler)
        server.mock_api = self.api
        self._server = server
        self._thread = Thread(target=server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the server and wait for its thread to exit."""
        if self._server is None:
            return

        server = self._server
        thread = self._thread
        server.shutdown()
        server.server_close()
        if thread is not None:
            thread.join()
        self._server = None
        self._thread = None

    def __enter__(self) -> "MockInsightsHTTPServer":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()
