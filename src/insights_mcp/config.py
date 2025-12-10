"""Configuration module for Insights MCP server.

This module centralizes all environment variable handling and configuration
to make settings easily reusable across different modules.
"""

import os

# Base URLs and endpoints
INSIGHTS_BASE_URL = os.getenv("INSIGHTS_BASE_URL") or "https://console.redhat.com"
INSIGHTS_PROXY_URL = os.getenv("INSIGHTS_PROXY_URL") or None  # Optional proxy URL for non Production environments
SSO_BASE_URL = os.getenv("SSO_BASE_URL") or "https://sso.redhat.com"
SSO_CONFIG_URL = f"{SSO_BASE_URL}/auth/realms/redhat-external/.well-known/openid-configuration"
SSO_TOKEN_ENDPOINT = f"{SSO_BASE_URL}/auth/realms/redhat-external/protocol/openid-connect/token"

# Authentication configuration
OAUTH_ENABLED = os.getenv("OAUTH_ENABLED", "false").lower() == "true"

# For OAuth_ENABLED:
# MCP server provides Dynamic Client Registration (DCR) Authentication via OAuth Proxy
SSO_CLIENT_ID = os.getenv("SSO_CLIENT_ID") or ""  # default to empty string if not set
SSO_CLIENT_SECRET = os.getenv("SSO_CLIENT_SECRET") or ""  # default to empty string if not set

# For OAUTH_ENABLED=False:
# MCP server requires no auth on MCP Client connection
INSIGHTS_CLIENT_ID = os.getenv("INSIGHTS_CLIENT_ID") or ""
INSIGHTS_CLIENT_SECRET = os.getenv("INSIGHTS_CLIENT_SECRET") or ""
INSIGHTS_REFRESH_TOKEN = os.getenv("INSIGHTS_REFRESH_TOKEN") or ""

# Argument toolset
INSIGHTS_MCP_TOOLSET = os.getenv("INSIGHTS_TOOLSET", "all")

SSO_OAUTH_TIMEOUT_SECONDS = os.getenv("SSO_OAUTH_TIMEOUT_SECONDS", 30)

FASTMCP_OAUTH_BASE_URL = os.getenv("FASTMCP_OAUTH_BASE_URL") or "http://localhost:8000"

# for backward compatibility
INSIGHTS_BASE_URL_PROD = INSIGHTS_BASE_URL
INSIGHTS_TOKEN_ENDPOINT_PROD = SSO_TOKEN_ENDPOINT
