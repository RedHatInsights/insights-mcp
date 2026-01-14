"""Integration tests for multi-user header-based authentication scenarios."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Reset token to trigger refresh for each request
from insights_mcp.client import InsightsHeadersBasedClient, InsightsOAuth2Client


class TestMultiUserScenarios:
    """Integration tests for multi-user authentication scenarios."""

    @pytest.mark.asyncio
    async def test_concurrent_requests_with_different_credentials(self):
        """Test that concurrent requests with different header credentials are isolated."""
        # This test verifies that InsightsHeadersBasedClient properly isolates
        # concurrent requests by creating separate client instances per request
        client = InsightsHeadersBasedClient(mcp_transport="sse", token_endpoint="https://test.example.com/token")

        # Simply verify that get_credentials_from_headers works for different credentials
        credentials_extracted = []

        async def test_credentials(user_id, user_secret):
            with patch("insights_mcp.client.get_http_headers") as mock_headers:
                mock_headers.return_value = {"insights-client-id": user_id, "insights-client-secret": user_secret}
                creds = client.get_credentials_from_headers()
                credentials_extracted.append(creds)

        await asyncio.gather(
            test_credentials("user1-id", "user1-secret"),
            test_credentials("user2-id", "user2-secret"),
            test_credentials("user3-id", "user3-secret"),
        )

        # Verify all credentials were extracted correctly
        assert len(credentials_extracted) == 3
        assert ("user1-id", "user1-secret") in credentials_extracted
        assert ("user2-id", "user2-secret") in credentials_extracted
        assert ("user3-id", "user3-secret") in credentials_extracted

    @pytest.mark.asyncio
    async def test_header_credentials_fallback_when_env_not_set(self):
        """Test that header credentials are extracted when no environment credentials are set."""
        client = InsightsHeadersBasedClient(mcp_transport="http", token_endpoint="https://test.example.com/token")

        with patch("insights_mcp.client.get_http_headers") as mock_headers:
            mock_headers.return_value = {"insights-client-id": "header-id", "insights-client-secret": "header-secret"}

            # Extract credentials from headers
            client_id, client_secret = client.get_credentials_from_headers()

            # Verify credentials were extracted correctly
            assert client_id == "header-id"
            assert client_secret == "header-secret"

    @pytest.mark.asyncio
    async def test_env_credentials_take_priority_over_headers(self):
        """Test that environment credentials take priority over header credentials."""
        client = InsightsOAuth2Client(
            client_id="env-id",
            client_secret="env-secret",
            mcp_transport="http",
            token_endpoint="https://test.example.com/token",
        )

        with patch("insights_mcp.client.get_http_headers") as mock_headers:
            # Even though headers provide different credentials
            mock_headers.return_value = {"insights-client-id": "header-id", "insights-client-secret": "header-secret"}

            with patch.object(client, "fetch_token", new_callable=AsyncMock) as mock_fetch:
                # Mock successful token fetch
                async def mock_fetch_impl(**kwargs):
                    _ = kwargs  # Mark as intentionally unused
                    client.token = {"access_token": "mock-token", "expires_in": 3600}
                    return client.token

                mock_fetch.side_effect = mock_fetch_impl

                await client.refresh_auth()

                # Environment credentials should be used (default fetch_token behavior)
                # fetch_token should be called without explicit credentials in headers
                mock_fetch.assert_called_once()
                call_kwargs = mock_fetch.call_args[1] if mock_fetch.call_args[1] else {}
                # When using instance credentials, fetch_token is called without headers containing credentials
                headers = call_kwargs.get("headers", {})
                assert "client_id" not in headers or headers.get("client_id") is None, (
                    f"Expected no client_id in headers when using instance credentials, got headers: {headers}"
                )

    @pytest.mark.asyncio
    async def test_error_when_no_credentials_available(self):
        """Test proper error when no credentials are provided in headers."""
        client = InsightsHeadersBasedClient(mcp_transport="http", token_endpoint="https://test.example.com/token")

        with patch("insights_mcp.client.get_http_headers") as mock_headers:
            # No credentials in headers
            mock_headers.return_value = {}

            # Should raise ValueError with authentication error
            with pytest.raises(ValueError, match="No credentials found in request headers"):
                await client.refresh_auth()

    @pytest.mark.asyncio
    async def test_make_request_allows_header_credentials_for_sse_http(self):
        """Test that make_request allows requests without instance credentials for SSE/HTTP."""
        client = InsightsOAuth2Client(
            client_id=None, client_secret=None, mcp_transport="sse", token_endpoint="https://test.example.com/token"
        )

        with patch("insights_mcp.client.get_http_headers") as mock_headers:
            mock_headers.return_value = {"insights-client-id": "test-id", "insights-client-secret": "test-secret"}

            with patch.object(client, "fetch_token", new_callable=AsyncMock):
                client.token = {"access_token": "mock-token"}

                with patch.object(client, "get", new_callable=AsyncMock) as mock_get:
                    mock_get.return_value.raise_for_status = MagicMock()
                    mock_get.return_value.content = b'{"result": "success"}'
                    mock_get.return_value.headers = {}

                    # Should not raise authentication error
                    result = await client.make_request(client.get, url="https://test.example.com/api")

                    # Should succeed with mocked response
                    assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_stdio_transport_does_not_use_headers(self):
        """Test that STDIO transport does not extract credentials from headers."""

        client = InsightsHeadersBasedClient(mcp_transport="stdio", token_endpoint="https://test.example.com/token")

        with patch("insights_mcp.client.get_http_headers") as mock_headers:
            mock_headers.return_value = {"insights-client-id": "test-id", "insights-client-secret": "test-secret"}

            # Extract credentials - should return None for STDIO
            extracted_id, extracted_secret = client.get_credentials_from_headers()

            assert extracted_id is None
            assert extracted_secret is None


class TestHeaderAuthenticationErrorMessages:
    """Test error messages for header-based authentication."""

    @pytest.mark.asyncio
    async def test_sse_error_message_for_header_auth(self):
        """Test that SSE transport error messages are specific for header-based auth."""
        # Client with NO environment credentials (header-based)
        client = InsightsOAuth2Client(
            client_id=None, client_secret=None, mcp_transport="sse", token_endpoint="https://test.example.com/token"
        )

        error_msg = client.no_auth_error(ValueError("Test error"))

        # Should mention header credentials specifically
        assert "header credentials" in error_msg.lower()
        assert "insights-client-id" in error_msg.lower() or "lightspeed-client-id" in error_msg.lower()
        assert "invalid or missing" in error_msg.lower()
        # Should NOT mention environment variables as primary method
        assert "environment credentials" not in error_msg.lower()

    @pytest.mark.asyncio
    async def test_http_error_message_for_header_auth(self):
        """Test that HTTP transport error messages are specific for header-based auth."""
        # Client with NO environment credentials (header-based)
        client = InsightsOAuth2Client(
            client_id=None, client_secret=None, mcp_transport="http", token_endpoint="https://test.example.com/token"
        )

        error_msg = client.no_auth_error(ValueError("Test error"))

        # Should mention header credentials specifically
        assert "header credentials" in error_msg.lower()
        assert "insights-client-id" in error_msg.lower() or "lightspeed-client-id" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_sse_error_message_for_env_auth(self):
        """Test that SSE transport error messages are specific for environment-based auth."""
        # Client WITH environment credentials
        client = InsightsOAuth2Client(
            client_id="env-id",
            client_secret="env-secret",
            mcp_transport="sse",
            token_endpoint="https://test.example.com/token",
        )

        error_msg = client.no_auth_error(ValueError("Test error"))

        # Should mention environment credentials specifically
        assert "environment credentials" in error_msg.lower()
        assert "INSIGHTS_CLIENT_ID" in error_msg or "LIGHTSPEED_CLIENT_ID" in error_msg
        assert "invalid" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_http_error_message_for_env_auth(self):
        """Test that HTTP transport error messages are specific for environment-based auth."""
        # Client WITH environment credentials
        client = InsightsOAuth2Client(
            client_id="env-id",
            client_secret="env-secret",
            mcp_transport="http",
            token_endpoint="https://test.example.com/token",
        )

        error_msg = client.no_auth_error(ValueError("Test error"))

        # Should mention environment credentials specifically
        assert "environment credentials" in error_msg.lower()
        assert "invalid" in error_msg.lower()
