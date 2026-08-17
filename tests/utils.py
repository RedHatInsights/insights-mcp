"""Utility functions for testing."""

import os


def has_insights_credentials() -> bool:
    """Return True when Insights service account credentials are available in the environment."""
    client_id = os.getenv("INSIGHTS_CLIENT_ID") or os.getenv("LIGHTSPEED_CLIENT_ID") or ""
    client_secret = os.getenv("INSIGHTS_CLIENT_SECRET") or os.getenv("LIGHTSPEED_CLIENT_SECRET") or ""
    return bool(client_id and client_secret)


def should_skip_insights_llm_tests() -> bool:
    """Check if LLM integration tests that call Insights APIs should be skipped."""
    return not has_insights_credentials()
