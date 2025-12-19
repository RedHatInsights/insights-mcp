"""Tests for version checking functionality in insights_mcp server."""

from unittest.mock import Mock, patch

import pytest
import requests

from insights_mcp.server import extract_version_sha, get_latest_release_tag, get_mcp_version


class TestExtractVersionSha:
    """Tests for extract_version_sha function."""

    @pytest.mark.parametrize(
        "version,expected_sha",
        [
            # Date-prefixed format extracts SHA
            ("20250905-072605-a8f7bd3a", "a8f7bd3a"),
            ("20240101-120000-abcdef12", "abcdef12"),
            ("20251219-235959-1234567890abcdef", "1234567890abcdef"),
            # Plain SHA passthrough
            ("a8f7bd3a", "a8f7bd3a"),
            ("abcdef12", "abcdef12"),
            ("1234567890abcdef", "1234567890abcdef"),
            # Edge cases
            ("0.0.0-dev", "0.0.0-dev"),
            ("v0.1.0", "v0.1.0"),
        ],
    )
    def test_extract_version_sha(self, version: str, expected_sha: str):
        """Test SHA extraction from various version formats."""
        assert extract_version_sha(version) == expected_sha

    def test_extract_version_sha_invalid_date_format(self):
        """Test that invalid date formats are passed through unchanged."""
        # Missing digits in date portion
        assert extract_version_sha("2025090-072605-a8f7bd3a") == "2025090-072605-a8f7bd3a"
        # Missing digits in time portion
        assert extract_version_sha("20250905-07260-a8f7bd3a") == "20250905-07260-a8f7bd3a"
        # Extra separator
        assert extract_version_sha("20250905-072605-extra-a8f7bd3a") == "extra-a8f7bd3a"


# pylint: disable=too-few-public-methods


class TestVersionComparison:
    """Tests for version comparison using SHA extraction."""

    @pytest.mark.parametrize(
        "current_version,latest_release",
        [
            # Same full version string
            ("20250905-072605-a8f7bd3a", "20250905-072605-a8f7bd3a"),
            # Same SHA, different dates (should match)
            ("20250905-072605-a8f7bd3a", "20251001-120000-a8f7bd3a"),
            # Date-prefixed vs plain SHA (should match)
            ("20250905-072605-a8f7bd3a", "a8f7bd3a"),
            ("a8f7bd3a", "20250905-072605-a8f7bd3a"),
            # Both plain SHAs
            ("a8f7bd3a", "a8f7bd3a"),
        ],
    )
    @patch("insights_mcp.server.get_latest_release_tag")
    def test_version_matches_with_sha_extraction(
        self, mock_get_latest_release_tag, current_version: str, latest_release: str
    ):
        """Test that versions with same SHA are detected as matching."""
        mock_get_latest_release_tag.return_value = latest_release

        with patch("insights_mcp.server.__version__", current_version):
            result = get_mcp_version()

        assert result == "You have the latest release"


@patch("insights_mcp.server.get_latest_release_tag")
@patch("insights_mcp.server.requests.get")
@patch("insights_mcp.server.__version__", "20250905-001953-16930107")
def test_version_check_with_updates_available(mock_requests_get, mock_get_latest_release_tag, mock_github_api_response):
    """Test version checking when updates are available."""
    # Mock the latest release tag
    mock_get_latest_release_tag.return_value = "20250905-072605-a8f7bd3a"

    # Mock the GitHub API response using fixture
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = mock_github_api_response
    mock_requests_get.return_value = mock_response

    # Call the function
    result = get_mcp_version()

    # Verify the result contains expected information
    assert "Latest release tag: 20250905-072605-a8f7bd3a" in result
    assert "Current version: 20250905-001953-16930107" in result
    assert "Add support for listing repositories from content sources" in result
    assert "2 commits ahead" in result

    # Verify API calls were made
    mock_get_latest_release_tag.assert_called_once()
    mock_requests_get.assert_called_once_with(
        (
            "https://api.github.com/repos/RedHatInsights/insights-mcp/compare/"
            "20250905-001953-16930107...20250905-072605-a8f7bd3a"
        ),
        timeout=30,
    )


@pytest.mark.parametrize("version", ["20250905-072605-a8f7bd3a", "20240101-120000-abcdef12"])
@patch("insights_mcp.server.get_latest_release_tag")
def test_version_check_same_version(mock_get_latest_release_tag, version):
    """Test version checking when current version matches latest release."""
    # Mock the latest release tag to match current version
    mock_get_latest_release_tag.return_value = version

    # Patch the __version__ to match the test parameter
    with patch("insights_mcp.server.__version__", version):
        result = get_mcp_version()

    # Verify the result is the expected message
    assert result == "You have the latest release"

    # Verify API call was made
    mock_get_latest_release_tag.assert_called_once()


@pytest.mark.integration
@patch("insights_mcp.server.__version__", "20250905-001953-16930107")
def test_version_check_real_github_api():
    """Test version checking with real GitHub API interaction."""
    # Call the function without mocking GitHub API
    result = get_mcp_version()

    # Verify the result contains expected structure
    assert "Latest release tag:" in result
    assert "Current version: 20250905-001953-16930107" in result
    assert "Compare:" in result
    # a specific commit message that should be in this range
    assert "Add support for listing repositories from content sources" in result

    # The result should be a string
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.integration
def test_version_check_real_api_same_version():
    """Test version checking with real API when versions might be the same."""
    # Get the actual latest release first
    try:
        latest_tag = get_latest_release_tag()

        # Patch the version to match the latest release
        with patch("insights_mcp.server.__version__", latest_tag):
            result = get_mcp_version()

        # If versions match, should get the "latest release" message
        assert result == "You have the latest release"

    except (requests.RequestException, KeyError, ValueError) as e:
        # If API call fails, skip this test
        pytest.skip(f"GitHub API not accessible: {e}")


@pytest.mark.integration
def test_get_latest_release_tag_real_api():
    """Test getting the latest release tag from real GitHub API."""
    try:
        latest_tag = get_latest_release_tag()

        # Verify the tag format (should be a non-empty string)
        assert isinstance(latest_tag, str)
        assert len(latest_tag) > 0

        # Tag should follow the expected format (YYYYMMDD-HHMMSS-XXXXXXXX)
        # This is a basic format check, not strict validation
        assert "-" in latest_tag

    except (requests.RequestException, KeyError, ValueError) as e:
        # If API call fails, skip this test
        pytest.skip(f"GitHub API not accessible: {e}")
