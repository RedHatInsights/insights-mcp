"""Test configuration for insights_mcp tests."""

import pytest


@pytest.fixture
def mock_github_api_response():
    """Mock GitHub API response for version comparison."""
    return {
        "commits": [
            {
                "commit": {
                    "message": (
                        "Add support for listing repositories from content sources\n\n"
                        "This commit adds functionality to list repositories."
                    )
                },
                "sha": "a8f7bd3a1234567890abcdef1234567890abcdef",
            },
            {
                "commit": {"message": "Fix authentication issue in client\n\nResolves authentication problems."},
                "sha": "1234567890abcdef1234567890abcdefa8f7bd3a",
            },
        ]
    }


@pytest.fixture
def mock_github_api_no_commits():
    """Mock GitHub API response when no commits difference."""
    return {"commits": []}
