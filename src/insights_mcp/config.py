import os

# Insights configuration
INSIGHTS_BASE_URL = os.getenv("INSIGHTS_BASE_URL") or "https://console.redhat.com"

# SSO configuration
SSO_BASE_URL = os.getenv("SSO_BASE_URL") or "https://sso.redhat.com"
SSO_CLIENT_ID = os.getenv("SSO_CLIENT_ID") or ""  # default to empty string if not set
SSO_CLIENT_SECRET = os.getenv("SSO_CLIENT_SECRET") or ""  # default to empty string if not set

SSO_CONFIG_URL = f"{SSO_BASE_URL}/auth/realms/redhat-external/.well-known/openid-configuration"
SSO_TOKEN_ENDPOINT = f"{SSO_BASE_URL}/auth/realms/redhat-external/protocol/openid-connect/token"


# for backward compatibility
INSIGHTS_BASE_URL_PROD = INSIGHTS_BASE_URL
INSIGHTS_TOKEN_ENDPOINT_PROD = SSO_TOKEN_ENDPOINT