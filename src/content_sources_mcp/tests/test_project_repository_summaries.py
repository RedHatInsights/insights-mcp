"""Tests for content-sources repository list projection and UUID checks."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from content_sources_mcp.server import (
    REPOSITORY_SUMMARY_FIELDS,
    _canonical_repository_uuid,
    mcp,
    project_repository_summaries,
)
from insights_mcp.errors import InsightsApiError

REPOSITORY_UUID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"


def test_project_repository_summaries_keeps_summary_fields_and_collection_metadata():
    """List projection keeps summary fields plus meta and links, and drops bulky fields."""
    response = {
        "meta": {"count": 1, "limit": 10, "offset": 0},
        "links": {"first": "/repositories/?limit=10&offset=0"},
        "data": [
            {
                "uuid": REPOSITORY_UUID,
                "name": "RHEL 9 BaseOS",
                "label": "rhel-9-baseos",
                "url": "https://cdn.redhat.com/content/dist/rhel9/9/x86_64/baseos/os",
                "origin": "red_hat",
                "content_type": "rpm",
                "distribution_versions": ["9"],
                "distribution_arch": "x86_64",
                "package_count": 4821,
                "build_count": 0,
                "version_count": 0,
                "status": "Valid",
                "gpg_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----\n\nmQINBG...\n",
                "last_snapshot": {"uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "content_counts": {"rpm": 4821}},
                "last_snapshot_task": {"uuid": "bbbbbbbb-cccc-dddd-eeee-ffffffffffff", "status": "completed"},
                "last_introspection_error": "",
                "account_id": "1234567",
                "org_id": "3340851",
            }
        ],
    }

    projected = project_repository_summaries(response)

    assert projected["meta"] == response["meta"]
    assert projected["links"] == response["links"]
    assert list(projected["data"][0]) == list(REPOSITORY_SUMMARY_FIELDS)
    assert projected["data"][0]["uuid"] == REPOSITORY_UUID
    assert projected["data"][0]["package_count"] == 4821
    assert "gpg_key" not in projected["data"][0]
    assert "last_snapshot" not in projected["data"][0]
    assert "last_snapshot_task" not in projected["data"][0]


def test_project_repository_summaries_omits_missing_summary_fields():
    """A repository that lacks optional counts does not gain empty keys."""
    projected = project_repository_summaries({"data": [{"uuid": REPOSITORY_UUID, "name": "custom-repo"}]})

    assert projected["data"][0] == {"uuid": REPOSITORY_UUID, "name": "custom-repo"}


@pytest.mark.parametrize(
    "response",
    [
        "not-json",
        ["not", "a", "collection"],
        {"meta": {"count": 0}},
        {"data": "unexpected"},
    ],
)
def test_project_repository_summaries_passes_non_collections_through(response):
    """Bodies that are not repository collections are returned unchanged."""
    assert project_repository_summaries(response) == response


def test_project_repository_summaries_keeps_non_dict_items():
    """Non-dict entries in data are left in place."""
    projected = project_repository_summaries({"data": ["unexpected-item"]})

    assert projected["data"] == ["unexpected-item"]


def test_canonical_repository_uuid_accepts_uppercase():
    """Uppercase UUID text is accepted and returned in canonical form."""
    assert _canonical_repository_uuid(REPOSITORY_UUID.upper()) == REPOSITORY_UUID


def test_canonical_repository_uuid_rejects_non_uuid():
    """A non-UUID value raises InsightsApiError and includes the bad value."""
    with pytest.raises(InsightsApiError, match="repository_uuid must be a UUID; got 'not-a-uuid'."):
        _canonical_repository_uuid("not-a-uuid")


@pytest.mark.asyncio
async def test_get_repository_returns_full_payload():
    """get_repository returns the unmodified single-repository API object."""
    repository = {
        "uuid": REPOSITORY_UUID,
        "name": "RHEL 9 BaseOS",
        "gpg_key": "-----BEGIN PGP PUBLIC KEY BLOCK-----\n\nmQINBG...\n",
        "last_snapshot": {"uuid": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"},
    }
    with patch.object(mcp.insights_client, "get", new_callable=AsyncMock, return_value=repository) as get_repository:
        result = json.loads(await mcp.get_repository(REPOSITORY_UUID))

    get_repository.assert_awaited_once_with(f"repositories/{REPOSITORY_UUID}")
    assert result == repository


@pytest.mark.asyncio
async def test_get_repository_rejects_invalid_uuid_without_calling_api():
    """An invalid UUID fails before the Insights API is called."""
    with patch.object(mcp.insights_client, "get", new_callable=AsyncMock) as get_repository:
        with pytest.raises(InsightsApiError, match="got 'repo-name'."):
            await mcp.get_repository("repo-name")

    get_repository.assert_not_awaited()
