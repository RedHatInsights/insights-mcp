"""Configuration module for Insights MCP server.

This module centralizes all environment variable handling and configuration
to make settings easily reusable across different modules.
"""

import os

# Base URLs and endpoints
INSIGHTS_BASE_URL = os.getenv("INSIGHTS_BASE_URL") or os.getenv("LIGHTSPEED_BASE_URL") or "https://console.redhat.com"
# Optional proxy URL for non Production environments
INSIGHTS_PROXY_URL = os.getenv("INSIGHTS_PROXY_URL") or os.getenv("LIGHTSPEED_PROXY_URL") or None
SSO_BASE_URL = (
    os.getenv("INSIGHTS_SSO_BASE_URL")
    or os.getenv("LIGHTSPEED_SSO_BASE_URL")
    or os.getenv("SSO_BASE_URL")
    or "https://sso.redhat.com"
)
SSO_CONFIG_URL = (
    os.getenv("SSO_CONFIG_URL") or f"{SSO_BASE_URL}/auth/realms/redhat-external/.well-known/openid-configuration"
)
SSO_TOKEN_ENDPOINT = (
    os.getenv("SSO_TOKEN_ENDPOINT") or f"{SSO_BASE_URL}/auth/realms/redhat-external/protocol/openid-connect/token"
)
SSO_OAUTH_TIMEOUT_SECONDS = int(os.getenv("SSO_OAUTH_TIMEOUT_SECONDS", "30"))

# Traditional service account credentials (stdio transport)
INSIGHTS_CLIENT_ID = os.getenv("INSIGHTS_CLIENT_ID") or ""
INSIGHTS_CLIENT_SECRET = os.getenv("INSIGHTS_CLIENT_SECRET") or ""
# if none is set, fallback to lightspeed credentials
if not INSIGHTS_CLIENT_ID and not INSIGHTS_CLIENT_SECRET:
    INSIGHTS_CLIENT_ID = os.getenv("LIGHTSPEED_CLIENT_ID") or ""
    INSIGHTS_CLIENT_SECRET = os.getenv("LIGHTSPEED_CLIENT_SECRET") or ""
INSIGHTS_REFRESH_TOKEN = os.getenv("INSIGHTS_REFRESH_TOKEN") or ""

# Argument toolset
INSIGHTS_MCP_TOOLSET = os.getenv("INSIGHTS_TOOLSET") or os.getenv("LIGHTSPEED_TOOLSET") or "all"

# Brand configuration for dynamic variable naming in user-facing messages
CONTAINER_BRAND = os.getenv("CONTAINER_BRAND", "insights")
# Strip "red-hat-" prefix if present (e.g., "red-hat-lightspeed" -> "lightspeed")
_brand_prefix = CONTAINER_BRAND.replace("red-hat-", "")
# Derive variable names dynamically for error messages
BRAND_CLIENT_ID_ENV = f"{_brand_prefix.upper()}_CLIENT_ID"
BRAND_CLIENT_SECRET_ENV = f"{_brand_prefix.upper()}_CLIENT_SECRET"
BRAND_CLIENT_ID_HEADER = f"{_brand_prefix.lower()}-client-id"
BRAND_CLIENT_SECRET_HEADER = f"{_brand_prefix.lower()}-client-secret"
