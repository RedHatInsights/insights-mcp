"""Tests for the monthly GitHub release changelog."""

from __future__ import annotations

import re
import subprocess
from datetime import date, datetime, timezone
from io import StringIO
from typing import Any

import pytest
from monthly_changelog import (
    RELEASES_PAGE_SIZE,
    ChangelogPlan,
    NotesWriteMode,
    Release,
    ReleaseUpdate,
    already_has_changelog,
    append_changelog,
    apply_changelog_plan,
    completed_months,
    edit_release_notes,
    extract_changed_lines,
    fetch_releases,
    gh_json_list,
    oldest_release_date,
    parse_repo,
    parse_today,
    previous_month,
    release_from_api,
    releases_api_path,
    releases_to_update,
    render_monthly_changelog,
    split_changes,
)

REPO = "RedHatInsights/insights-mcp"

CLUSTER_LINE = (
    "* [CCXDEV-16884] Adding cluster list tool by @joselsegura in "
    "https://github.com/RedHatInsights/insights-mcp/pull/468"
)
KONFLUX_458 = (
    "* chore(deps): lock file maintenance by @red-hat-konflux[bot] in "
    "https://github.com/RedHatInsights/insights-mcp/pull/458"
)
KONFLUX_473 = (
    "* Lock file maintenance by @red-hat-konflux[bot] in https://github.com/RedHatInsights/insights-mcp/pull/473"
)
KONFLUX_441 = (
    "* chore(deps): lock file maintenance by @red-hat-konflux[bot] in "
    "https://github.com/RedHatInsights/insights-mcp/pull/441"
)
CATALOG_LINE = (
    "* Make catalog fetching fail more visible by @matej-lohnicky in "
    "https://github.com/RedHatInsights/insights-mcp/pull/453"
)
DOC_LINKS_LINE = (
    "* fix broken documentation links by @matej-lohnicky in https://github.com/RedHatInsights/insights-mcp/pull/444"
)
PLAYBOOK_LINE = (
    "* remove dead remediation playbook link (RHIN-2503) by @matej-lohnicky in "
    "https://github.com/RedHatInsights/insights-mcp/pull/443"
)
CONTRIBUTOR_LINE = (
    "* @joselsegura made their first contribution in https://github.com/RedHatInsights/insights-mcp/pull/468"
)
NOVEMBER_LINE = (
    "* Pin the GitHub runner from the version file by @fschulle in "
    "https://github.com/RedHatInsights/insights-mcp/pull/470"
)
FULL_CHANGELOG = (
    "**Full Changelog**: https://github.com/RedHatInsights/insights-mcp/compare/"
    "20261016-102642-628258bf...20261020-125625-c9df93ec"
)

OCTOBER_NEWEST = "20261022-103031-6d558022"
OCTOBER_HUMAN = "20261020-125625-c9df93ec"
OCTOBER_KONFLUX = "20261008-130555-68dc71d2"
SEPTEMBER_NEWEST = "20260930-110646-ae97aecb"
SEPTEMBER_KONFLUX = "20260922-082329-89b3ef05"
AUGUST_NEWEST = "20260831-135846-a18077a5"
AUGUST_OLDER = "20260813-210327-be1364ff"
NOVEMBER_TAG = "20261106-075711-a5f831cb"


def release_notes(bullets: list[str], contributors: list[str] | None = None) -> str:
    """Return GitHub-style notes for the given What's Changed bullets."""
    lines = ["## What's Changed", *bullets, ""]
    if contributors:
        lines.extend(["## New Contributors", *contributors, ""])
    lines.append(FULL_CHANGELOG)
    return "\n".join(lines) + "\n"


def make_release(tag: str, published_at: str, body: str) -> Release:
    """Return a release published at an ISO-8601 instant."""
    return Release(
        tag=tag,
        published_at=datetime.fromisoformat(published_at),
        body=body,
        url=f"https://github.com/{REPO}/releases/tag/{tag}",
    )


def api_release(
    tag: str,
    published_at: str,
    body: str = "",
    *,
    draft: bool = False,
) -> dict[str, Any]:
    """Return one GitHub releases API object."""
    return {
        "tag_name": tag,
        "published_at": published_at,
        "body": body,
        "html_url": f"https://github.com/{REPO}/releases/tag/{tag}",
        "draft": draft,
    }


def expected_prior(release: Release) -> str:
    """Return the prior-release line for ``release``."""
    return f"Prior monthly release: [{release.tag}]({release.url})"


def test_completed_months_excludes_the_current_month_and_wraps_the_year():
    """November asks for October then September. January wraps to the prior year."""
    assert completed_months(date(2026, 11, 6), 2) == [(2026, 10), (2026, 9)]
    assert completed_months(date(2026, 1, 6), 2) == [(2025, 12), (2025, 11)]


def test_completed_months_rejects_a_non_positive_count():
    """A window of zero months is rejected with the actual value."""
    with pytest.raises(ValueError, match="invalid months 0: want >= 1"):
        completed_months(date(2026, 11, 6), 0)


def test_previous_month_rejects_a_month_outside_the_calendar():
    """Month 13 is not a calendar month."""
    with pytest.raises(ValueError, match="invalid month 13: want 1..12"):
        previous_month(2026, 13)


def test_oldest_release_date_includes_the_month_before_the_window():
    """Two months from November still need August, for September's prior link."""
    assert oldest_release_date(date(2026, 11, 6), 2) == date(2026, 8, 1)


def test_extract_changed_lines_keeps_bullets_and_drops_the_rest():
    """What's Changed bullets stay. Contributors and the compare link do not."""
    body = release_notes([CLUSTER_LINE, "- dash bullet with no pull request"], [CONTRIBUTOR_LINE])
    assert extract_changed_lines(body) == [CLUSTER_LINE, "- dash bullet with no pull request"]


def test_already_has_changelog_matches_only_the_heading_line():
    """A mention of the heading inside a bullet is not the section."""
    assert already_has_changelog("* see ## Monthly Changelog in the discussion\n") is False
    assert already_has_changelog("## Monthly Changelog\n") is True
    assert already_has_changelog("## Monthly Changelog   \n") is True


def test_split_changes_moves_konflux_lines_and_drops_duplicate_pull_requests():
    """The first copy of a pull request wins. Konflux lines go in the auto list."""
    human_lines, auto_lines = split_changes([CLUSTER_LINE, KONFLUX_458, CLUSTER_LINE, KONFLUX_473, "- plain note"])
    assert human_lines == [CLUSTER_LINE, "- plain note"]
    assert auto_lines == [KONFLUX_458, KONFLUX_473]


def test_render_monthly_changelog_places_prior_release_between_the_lists():
    """Human edits, the previous month's release, then Konflux updates."""
    prior = make_release(SEPTEMBER_NEWEST, "2026-09-30T11:12:46Z", "")
    section = render_monthly_changelog([CLUSTER_LINE], [KONFLUX_458, KONFLUX_473], prior)
    assert section == "\n".join(
        [
            "---",
            "## Monthly Changelog",
            CLUSTER_LINE,
            "",
            expected_prior(prior),
            "",
            "### Auto updates",
            KONFLUX_458,
            KONFLUX_473,
            "---",
            "",
        ]
    )


def test_render_monthly_changelog_keeps_empty_sections_and_names_a_missing_prior():
    """Both headings are written when a month has no matching bullets."""
    section = render_monthly_changelog([], [], None)
    assert section == "\n".join(
        [
            "---",
            "## Monthly Changelog",
            "",
            "Prior monthly release: none",
            "",
            "### Auto updates",
            "---",
            "",
        ]
    )


def test_append_changelog_keeps_the_original_notes():
    """The new section follows the existing notes. Blank notes are replaced by the section."""
    section = "---\n## Monthly Changelog\n---\n"
    assert append_changelog("## What's Changed\n* kept\n", section) == (
        "## What's Changed\n* kept\n\n---\n## Monthly Changelog\n---\n"
    )
    assert append_changelog("  \n", section) == section


def test_release_from_api_parses_zulu_time_and_skips_drafts():
    """Zulu timestamps are UTC. A draft is not a published release."""
    release = release_from_api(api_release(OCTOBER_NEWEST, "2026-10-22T10:40:05Z", KONFLUX_473))
    assert release == Release(
        tag=OCTOBER_NEWEST,
        published_at=datetime(2026, 10, 22, 10, 40, 5, tzinfo=timezone.utc),
        body=KONFLUX_473,
        url=f"https://github.com/{REPO}/releases/tag/{OCTOBER_NEWEST}",
    )
    assert release_from_api(api_release(OCTOBER_NEWEST, "2026-10-22T10:40:05Z", draft=True)) is None


def test_release_from_api_rejects_missing_and_invalid_fields():
    """Published releases need a tag, a zoned timestamp, a URL, and a string body."""
    with pytest.raises(ValueError, match="invalid tag_name None: want a non-empty string"):
        release_from_api({})
    missing_time = api_release(OCTOBER_NEWEST, "2026-10-22T10:40:05Z")
    missing_time["published_at"] = None
    with pytest.raises(ValueError, match=f"release {OCTOBER_NEWEST!r} has no published_at: got None"):
        release_from_api(missing_time)
    invalid_time = api_release(OCTOBER_NEWEST, "yesterday")
    with pytest.raises(ValueError, match="invalid published_at 'yesterday': want ISO-8601"):
        release_from_api(invalid_time)
    unzoned = api_release(OCTOBER_NEWEST, "2026-10-22T10:40:05")
    with pytest.raises(ValueError, match="published_at '2026-10-22T10:40:05' has no timezone"):
        release_from_api(unzoned)
    numeric_body = api_release(OCTOBER_NEWEST, "2026-10-22T10:40:05Z")
    numeric_body["body"] = 5
    with pytest.raises(ValueError, match="body: want a string, got int"):
        release_from_api(numeric_body)
    empty_notes = api_release(OCTOBER_NEWEST, "2026-10-22T10:40:05Z")
    empty_notes["body"] = None
    parsed = release_from_api(empty_notes)
    assert parsed is not None
    assert parsed.body == ""


def test_fetch_releases_stops_after_the_cutoff_page():
    """A full page is followed. The page that passes August is the last one read."""
    october = [
        api_release(f"20261022-103031-{index:08x}", "2026-10-22T10:40:05Z") for index in range(RELEASES_PAGE_SIZE)
    ]
    pages = {
        1: october,
        2: [
            api_release("20261021-000000-ddddddd1", "2026-10-21T00:00:00Z", draft=True),
            api_release(AUGUST_NEWEST, "2026-08-31T14:07:11Z", "august"),
            api_release("20260731-120000-ccccccc1", "2026-07-31T12:00:00Z", "july"),
        ],
        3: [api_release("20261001-000000-eeeeeee1", "2026-10-01T00:00:00Z")],
    }
    calls: list[str] = []

    def api(path: str) -> list[dict[str, Any]]:
        calls.append(path)
        page = int(path.rsplit("=", 1)[1])
        return pages[page]

    releases = fetch_releases(REPO, date(2026, 8, 1), api)
    tags = [release.tag for release in releases]
    assert tags[0] == october[0]["tag_name"]
    assert tags[-1] == AUGUST_NEWEST
    assert len(tags) == RELEASES_PAGE_SIZE + 1
    assert "20260731-120000-ccccccc1" not in tags
    assert "20261021-000000-ddddddd1" not in tags
    assert calls == [releases_api_path(REPO, 1), releases_api_path(REPO, 2)]


def test_fetch_releases_stops_on_a_short_page():
    """A page shorter than the page size is the last page."""
    pages = {
        1: [api_release(OCTOBER_NEWEST, "2026-10-22T10:40:05Z")],
        2: [api_release("20261001-000000-eeeeeee1", "2026-10-01T00:00:00Z")],
    }
    calls: list[str] = []

    def api(path: str) -> list[dict[str, Any]]:
        calls.append(path)
        return pages[int(path.rsplit("=", 1)[1])]

    releases = fetch_releases(REPO, date(2026, 8, 1), api)
    assert [release.tag for release in releases] == [OCTOBER_NEWEST]
    assert calls == [releases_api_path(REPO, 1)]


def test_gh_json_list_returns_release_objects(monkeypatch: pytest.MonkeyPatch):
    """A successful gh api call is parsed as a list of objects."""

    def fake_run(
        args: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        assert args == ["gh", "api", releases_api_path(REPO, 1)]
        assert kwargs["capture_output"] is True
        assert kwargs["check"] is False
        assert kwargs["text"] is True
        return subprocess.CompletedProcess(args, 0, stdout="[]", stderr="")

    monkeypatch.setattr("monthly_changelog.subprocess.run", fake_run)
    assert not gh_json_list(releases_api_path(REPO, 1))


def test_gh_json_list_reports_gh_and_shape_failures(monkeypatch: pytest.MonkeyPatch):
    """A failed gh process and a JSON object are both errors that name the path."""
    path = releases_api_path(REPO, 1)
    responses = iter(
        [
            subprocess.CompletedProcess(["gh"], 1, stdout="", stderr="bad credentials"),
            subprocess.CompletedProcess(["gh"], 0, stdout='{"message": "nope"}', stderr=""),
        ]
    )

    def fake_run(_args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return next(responses)

    monkeypatch.setattr("monthly_changelog.subprocess.run", fake_run)
    with pytest.raises(RuntimeError, match=re.escape(f"gh api {path} failed: bad credentials")):
        gh_json_list(path)
    with pytest.raises(ValueError, match=re.escape(f"gh api {path}: want a list, got dict")):
        gh_json_list(path)


def test_edit_release_notes_sends_the_body_on_stdin(monkeypatch: pytest.MonkeyPatch):
    """gh release edit reads the full notes from stdin."""
    seen: dict[str, object] = {}

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        seen["args"] = args
        seen["input"] = kwargs["input"]
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr("monthly_changelog.subprocess.run", fake_run)
    edit_release_notes(REPO, OCTOBER_NEWEST, "notes\n")
    assert seen["args"] == [
        "gh",
        "release",
        "edit",
        OCTOBER_NEWEST,
        "--repo",
        REPO,
        "--notes-file",
        "-",
    ]
    assert seen["input"] == "notes\n"


def test_edit_release_notes_includes_gh_stderr(monkeypatch: pytest.MonkeyPatch):
    """A rejected edit names the tag and the gh error."""

    def fake_run(_args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(["gh"], 1, stdout="", stderr="denied")

    monkeypatch.setattr("monthly_changelog.subprocess.run", fake_run)
    with pytest.raises(RuntimeError, match=f"gh release edit {OCTOBER_NEWEST} failed: denied"):
        edit_release_notes(REPO, OCTOBER_NEWEST, "notes\n")


def test_releases_to_update_summarizes_the_last_two_completed_months():
    """October and September are summarized. November is left alone. August is only a link."""
    october_newest_body = release_notes([KONFLUX_473, CLUSTER_LINE])
    october_newest = make_release(OCTOBER_NEWEST, "2026-10-22T10:40:05Z", october_newest_body)
    october_human = make_release(
        OCTOBER_HUMAN,
        "2026-10-20T13:03:43Z",
        release_notes([CLUSTER_LINE], [CONTRIBUTOR_LINE]),
    )
    october_konflux = make_release(
        OCTOBER_KONFLUX,
        "2026-10-08T13:14:14Z",
        release_notes([KONFLUX_458]),
    )
    september_body = release_notes([CATALOG_LINE, DOC_LINKS_LINE, PLAYBOOK_LINE])
    september_newest = make_release(SEPTEMBER_NEWEST, "2026-09-30T11:12:46Z", september_body)
    september_konflux = make_release(
        SEPTEMBER_KONFLUX,
        "2026-09-22T08:31:31Z",
        release_notes([KONFLUX_441]),
    )
    august_newest = make_release(AUGUST_NEWEST, "2026-08-31T14:07:11Z", release_notes([CLUSTER_LINE]))
    august_older = make_release(AUGUST_OLDER, "2026-08-13T21:11:02Z", release_notes([KONFLUX_441]))
    november = make_release(NOVEMBER_TAG, "2026-11-06T08:04:27Z", release_notes([NOVEMBER_LINE]))
    plan = releases_to_update(
        [
            november,
            october_newest,
            october_human,
            october_konflux,
            september_newest,
            september_konflux,
            august_older,
            august_newest,
        ],
        date(2026, 11, 6),
        2,
    )
    assert not plan.skipped_tags
    assert [update.tag for update in plan.updates] == [OCTOBER_NEWEST, SEPTEMBER_NEWEST]

    october_section = "\n".join(
        [
            "---",
            "## Monthly Changelog",
            CLUSTER_LINE,
            "",
            expected_prior(september_newest),
            "",
            "### Auto updates",
            KONFLUX_458,
            KONFLUX_473,
            "---",
            "",
        ]
    )
    assert plan.updates[0].body == append_changelog(october_newest_body, october_section)
    october_monthly = plan.updates[0].body.split("## Monthly Changelog", 1)[1]
    assert "first contribution" not in october_monthly
    assert "Full Changelog" not in october_monthly
    assert october_monthly.count("pull/468") == 1
    assert NOVEMBER_LINE not in plan.updates[0].body

    september_section = "\n".join(
        [
            "---",
            "## Monthly Changelog",
            CATALOG_LINE,
            DOC_LINKS_LINE,
            PLAYBOOK_LINE,
            "",
            expected_prior(august_newest),
            "",
            "### Auto updates",
            KONFLUX_441,
            "---",
            "",
        ]
    )
    assert plan.updates[1].body == append_changelog(september_body, september_section)
    assert AUGUST_NEWEST not in [update.tag for update in plan.updates]
    assert NOVEMBER_TAG not in [update.tag for update in plan.updates]


def test_releases_to_update_skips_a_release_that_already_has_the_heading():
    """The newest October release is left unchanged. September is still filled in."""
    october = make_release(
        OCTOBER_NEWEST,
        "2026-10-22T10:40:05Z",
        "notes\n\n## Monthly Changelog\n",
    )
    september = make_release(
        SEPTEMBER_NEWEST,
        "2026-09-30T11:12:46Z",
        release_notes([CATALOG_LINE]),
    )
    plan = releases_to_update([october, september], date(2026, 11, 6), 2)
    assert plan.skipped_tags == (OCTOBER_NEWEST,)
    assert [update.tag for update in plan.updates] == [SEPTEMBER_NEWEST]
    assert "Prior monthly release: none" in plan.updates[0].body


def test_releases_to_update_groups_a_zoned_timestamp_by_utc_month():
    """00:30 on 1 November in UTC+2 is still 31 October in UTC."""
    release = make_release(
        "20261101-003000-ccccccc1",
        "2026-11-01T00:30:00+02:00",
        release_notes([CLUSTER_LINE]),
    )
    plan = releases_to_update([release], date(2026, 11, 6), 1)
    assert [update.tag for update in plan.updates] == ["20261101-003000-ccccccc1"]


def test_releases_to_update_rejects_a_naive_timestamp():
    """A release time without a timezone is an error, not a local-time guess."""
    release = Release(
        tag=OCTOBER_NEWEST,
        published_at=datetime(2026, 10, 22, 10, 40, 5),
        body="",
        url=f"https://github.com/{REPO}/releases/tag/{OCTOBER_NEWEST}",
    )
    with pytest.raises(ValueError, match=f"release {OCTOBER_NEWEST!r} published_at .* has no timezone"):
        releases_to_update([release], date(2026, 11, 6), 1)


def test_apply_changelog_plan_dry_run_prints_notes_without_editing():
    """Dry run lists skips and the new notes. The edit callback is not called."""
    calls: list[tuple[str, str, str]] = []

    def edit(repo: str, tag: str, body: str) -> None:
        calls.append((repo, tag, body))

    plan = ChangelogPlan(
        updates=(ReleaseUpdate(tag=OCTOBER_NEWEST, body="notes\n"),),
        skipped_tags=(SEPTEMBER_NEWEST,),
    )
    output = StringIO()
    apply_changelog_plan(REPO, plan, NotesWriteMode.DRY_RUN, edit, output)
    assert not calls
    text = output.getvalue()
    assert text == (f"Skipped {SEPTEMBER_NEWEST}: monthly changelog already present\n--- {OCTOBER_NEWEST} ---\nnotes\n")


def test_apply_changelog_plan_edit_writes_each_update():
    """Edit mode logs the full body before sending it and prints the tag after."""
    calls: list[tuple[str, str, str]] = []

    def edit(repo: str, tag: str, body: str) -> None:
        calls.append((repo, tag, body))

    plan = ChangelogPlan(updates=(ReleaseUpdate(tag=OCTOBER_NEWEST, body="notes\n"),), skipped_tags=())
    output = StringIO()
    apply_changelog_plan(REPO, plan, NotesWriteMode.EDIT, edit, output)
    assert calls == [(REPO, OCTOBER_NEWEST, "notes\n")]
    assert output.getvalue() == (f"--- {OCTOBER_NEWEST} ---\nnotes\nUpdated {OCTOBER_NEWEST}\n")


def test_apply_changelog_plan_says_when_there_is_nothing_to_do():
    """An empty window prints one line and does not edit."""
    calls: list[tuple[str, str, str]] = []

    def edit(repo: str, tag: str, body: str) -> None:
        calls.append((repo, tag, body))

    output = StringIO()
    apply_changelog_plan(REPO, ChangelogPlan(updates=(), skipped_tags=()), NotesWriteMode.EDIT, edit, output)
    assert not calls
    assert output.getvalue() == "No releases to update.\n"


def test_parse_repo_and_today_name_the_bad_value():
    """Repo and date errors include the value that was rejected."""
    assert parse_repo(REPO) == REPO
    assert parse_today("2026-11-06") == date(2026, 11, 6)
    with pytest.raises(ValueError, match="invalid repo 'insights-mcp': want owner/name"):
        parse_repo("insights-mcp")
    with pytest.raises(ValueError, match="invalid today 'yesterday': want YYYY-MM-DD"):
        parse_today("yesterday")
