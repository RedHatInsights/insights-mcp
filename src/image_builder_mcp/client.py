"""Image Builder MCP client for interacting with the Image Builder API."""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from fastmcp.server.dependencies import get_http_headers

import requests


class ImageBuilderClient:  # pylint: disable=too-many-instance-attributes
    """Client for interacting with the Red Hat Image Builder API.

    This client handles authentication, token management, and API requests
    to the Image Builder service.
    """

    def __init__(  # pylint: disable=too-many-arguments
            self,
            client_id: Optional[str],
            client_secret: Optional[str],
            stage: Optional[bool] = False,
            proxy_url: Optional[str] = None,
            image_builder_mcp_client_id: str = "mcp",
            oauth_enabled: bool = False
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self.stage = stage
        self.proxy_url = proxy_url
        self.image_builder_mcp_client_id = image_builder_mcp_client_id
        self.oauth_enabled = oauth_enabled
        self.logger = logging.getLogger("ImageBuilderClient")

        if self.stage:
            self.domain = "console.stage.redhat.com"
            self.sso_domain = "sso.stage.redhat.com"
        else:
            self.domain = "console.redhat.com"
            self.sso_domain = "sso.redhat.com"
        self.base_url = f"https://{self.domain}/api/image-builder/v1"

    def get_token(self) -> str:
        """Get or refresh the authentication token."""
        if self.oauth_enabled:
            self.logger.debug("OAuth is enabled, skipping token management")
            return ""
        if self.token and self.token_expiry and datetime.now() < self.token_expiry:
            self.logger.debug(
                "Using cached token valid until %s", self.token_expiry)
            # mypy doesn't understand that self.token is not None after the check above
            assert self.token is not None
            return self.token
        self.logger.debug("Fetching new token")
        token_url = f"https://{self.sso_domain}/auth/realms/redhat-external/protocol/openid-connect/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        response = requests.post(token_url, data=data, timeout=60)
        response.raise_for_status()

        token_data = response.json()
        self.token = token_data["access_token"]
        # Set token expiry to 5 minutes before actual expiry to ensure we refresh in time
        self.token_expiry = datetime.now(
        ) + timedelta(seconds=token_data["expires_in"] - 300)

        # Ensure we return a string (self.token was just assigned above)
        assert self.token is not None
        return self.token

    def make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """Make an authenticated request to the Image Builder API."""
        headers = {
            "Content-Type": "application/json",
            "X-ImageBuilder-ui": self.image_builder_mcp_client_id
        }

        if self.oauth_enabled:
            caller_headers_auth = get_http_headers().get("authorization")
            if caller_headers_auth:
                # If the request is authenticated, use the caller's authorization header
                # This is useful for OAuth flows where the client is already authenticated
                headers["authorization"] = caller_headers_auth
        elif self.client_id and self.client_secret:
            headers["authorization"] = f"Bearer {self.get_token()}"

        # else no authentication, use public API

        url = f"{self.base_url}/{endpoint}"
        self.logger.debug("Making %s request to %s with data %s", method, url, data)

        proxies = None
        if self.stage and self.proxy_url:
            proxy = self.proxy_url
            proxies = {
                "http": proxy,
                "https": proxy
            }

        response = requests.request(method, url, headers=headers, json=data, params=params, proxies=proxies, timeout=60)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # try to append the details to the error
            try:
                ret = response.json()
                raise type(e)(f"{str(e)} - Response: {ret}") from e
            except json.JSONDecodeError:
                # ignore the JSONDecodeError and raise the original error
                raise e from None
        ret = response.json()
        self.logger.debug("Response from %s: %s", url, json.dumps(ret, indent=2))

        return ret

    def no_auth_error(self, e: Exception, transport: Optional[str] = None) -> str:
        """Generate authentication error message based on transport type."""
        base_message = (
            "[INSTRUCTION] Tell the user that the MCP server setup is not valid! "
            "The user should go to [https://console.redhat.com](https://console.redhat.com) to "
            "'YOUR USER' ➡ My User Access ➡ Service Accounts create a service account and then set the "
        )

        if transport in ["sse", "http"]:
            return (
                f"{base_message}header variables `insights-client-id` and "
                "`insights-client-secret` in your request.\n"
                "Here is the direct link for the user's convenience: "
                "[https://console.redhat.com/iam/service-accounts](https://console.redhat.com/iam/service-accounts) "
                "Come up with a detailed description of this for the user. "
                "Only describe this, don't expose details about the tool function itself. "
                f"Don't proceed with the request before this is fixed. Error: {str(e)}."
            )

        return (
            f"{base_message}`INSIGHTS_CLIENT_ID` and `INSIGHTS_CLIENT_SECRET` "
            "in your mcp.json config.\n"
            "Here is the direct link for the user's convenience: "
            "[https://console.redhat.com/iam/service-accounts](https://console.redhat.com/iam/service-accounts) "
            "Come up with a detailed description of this for the user. "
            "Only describe this, don't expose details about the tool function itself. "
            f"Don't proceed with the request before this is fixed. Error: {str(e)}."
        )
