#!/usr/bin/env python3
"""Append a monthly changelog to the newest GitHub release of recent months.

The job runs after a month has closed. It summarizes every release published
in that month onto the newest one, and it repeats the previous month so a
missed run is filled in on the next one.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, TextIO, assert_never

MONTHLY_CHANGELOG_HEADING_PREFIX = "## Monthly Changelog Summary"
AUTO_UPDATES_HEADING = "### Auto updates"
WHATS_CHANGED_HEADING = "## What's Changed"
KONFLUX_MARKER = "@red-hat-konflux[bot]"
RELEASES_PAGE_SIZE = 100

_PULL_REQUEST_URL_RE = re.compile(r"https://github\.com/[^/\s]+/[^/\s]+/pull/\d+")
_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


class NotesWriteMode(Enum):
    """Whether updated notes are written to GitHub or only printed."""

    EDIT = "edit"
    DRY_RUN = "dry-run"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Release:
    """One published GitHub release.

    ``published_at`` is timezone-aware. Month boundaries use UTC.
    """

    tag: str
    published_at: datetime
    body: str
    url: str

    def __str__(self) -> str:
        return self.tag


@dataclass(frozen=True)
class ReleaseUpdate:
    """A release whose notes should gain a monthly changelog."""

    tag: str
    body: str

    def __str__(self) -> str:
        return self.tag


@dataclass(frozen=True)
class ChangelogPlan:
    """Edits and skips for one run, newest target month first."""

    updates: tuple[ReleaseUpdate, ...]
    skipped_tags: tuple[str, ...]


def completed_months(today: date, count: int) -> list[tuple[int, int]]:
    """Return completed calendar months before ``today``, newest first.

    Args:
        today: The day the job runs. That month is excluded.
        count: How many previous months to return.

    Returns:
        ``(year, month)`` pairs. Month is 1 through 12.

    Raises:
        ValueError: ``count`` is less than 1.
    """
    if count < 1:
        raise ValueError(f"invalid months {count}: want >= 1")
    year = today.year
    month = today.month
    months: list[tuple[int, int]] = []
    for _ in range(count):
        year, month = previous_month(year, month)
        months.append((year, month))
    return months


def previous_month(year: int, month: int) -> tuple[int, int]:
    """Return the calendar month before ``year``/``month``.

    Args:
        year: Calendar year.
        month: Month number, 1 through 12.

    Returns:
        ``(year, month)`` of the previous month.

    Raises:
        ValueError: ``month`` is outside 1 through 12.
    """
    if month == 1:
        return year - 1, 12
    if month < 1 or month > 12:
        raise ValueError(f"invalid month {month}: want 1..12")
    return year, month - 1


def oldest_release_date(today: date, months: int) -> date:
    """Return the first day that release listing must reach.

    The oldest changelog links to the newest release of the month before it,
    so the listing starts one month earlier than the edit window.

    Args:
        today: The day the job runs.
        months: Completed months to update.

    Returns:
        The first day of that prior month.

    Raises:
        ValueError: ``months`` is less than 1.
    """
    year, month = completed_months(today, months)[-1]
    prior_year, prior_month = previous_month(year, month)
    return date(prior_year, prior_month, 1)


def parse_published_at(value: str, tag: str) -> datetime:
    """Return ``value`` as a UTC datetime.

    Args:
        value: GitHub ``published_at``, for example ``2026-10-22T10:40:05Z``.
        tag: Release tag, included in errors.

    Returns:
        The same instant in UTC.

    Raises:
        ValueError: ``value`` is not ISO-8601 or has no timezone.
    """
    try:
        published_at = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"release {tag!r} has invalid published_at {value!r}: want ISO-8601") from exc
    if published_at.tzinfo is None:
        raise ValueError(f"release {tag!r} published_at {value!r} has no timezone")
    return published_at.astimezone(timezone.utc)


def release_from_api(item: dict[str, Any]) -> Release | None:
    """Build a release from one GitHub API object.

    Args:
        item: One element of ``GET /repos/{owner}/{repo}/releases``.

    Returns:
        The release, or None when ``item`` is a draft.

    Raises:
        ValueError: A published release is missing a tag, time, or URL,
            or the time is not ISO-8601.
    """
    tag = item.get("tag_name")
    if not isinstance(tag, str) or tag == "":
        raise ValueError(f"invalid tag_name {tag!r}: want a non-empty string")
    if item.get("draft") is True:
        return None
    published_raw = item.get("published_at")
    if not isinstance(published_raw, str) or published_raw == "":
        raise ValueError(f"release {tag!r} has no published_at: got {published_raw!r}")
    url = item.get("html_url")
    if not isinstance(url, str) or url == "":
        raise ValueError(f"release {tag!r} has no html_url: got {url!r}")
    body = item.get("body")
    # GitHub uses null for a release that has no notes.
    if body is None:
        body = ""
    if not isinstance(body, str):
        raise ValueError(f"release {tag!r} body: want a string, got {type(body).__name__}")
    return Release(
        tag=tag,
        published_at=parse_published_at(published_raw, tag),
        body=body,
        url=url,
    )


def published_utc(release: Release) -> datetime:
    """Return ``release.published_at`` in UTC.

    Args:
        release: Release whose timestamp is checked.

    Returns:
        The publish time in UTC.

    Raises:
        ValueError: The timestamp has no timezone.
    """
    if release.published_at.tzinfo is None:
        published = release.published_at.isoformat()
        raise ValueError(f"release {release.tag!r} published_at {published} has no timezone")
    return release.published_at.astimezone(timezone.utc)


def extract_changed_lines(body: str) -> list[str]:
    """Return bullet lines from the What's Changed section.

    Args:
        body: GitHub release notes.

    Returns:
        ``* `` and ``- `` lines after ``## What's Changed`` and before the
        next heading. Contributor lists and the full-changelog link are omitted.
    """
    lines: list[str] = []
    in_section = False
    for line in body.splitlines():
        if line.strip() == WHATS_CHANGED_HEADING:
            in_section = True
            continue
        if not in_section:
            continue
        if line.startswith("## ") or line.startswith("**Full Changelog**"):
            break
        if line.startswith("* ") or line.startswith("- "):
            lines.append(line)
    return lines


def format_month_year_label(year: int, month: int) -> str:
    """Return a full month name and year, for example ``October 2026``."""
    return date(year, month, 1).strftime("%B %Y")


def monthly_changelog_heading(year: int, month: int) -> str:
    """Return the monthly changelog section heading for ``year``/``month``."""
    return f"{MONTHLY_CHANGELOG_HEADING_PREFIX} - {format_month_year_label(year, month)}"


def monthly_changelog_badge(year: int, month: int) -> str:
    """Return a shields.io badge line for the monthly changelog month."""
    label = format_month_year_label(year, month)
    badge_value = label.replace(" ", "_")
    alt = f"Monthly Changelog Summary {label}"
    url = f"https://img.shields.io/badge/Monthly_Release-{badge_value}-blue"
    return f"![{alt}]({url})"


def already_has_changelog(body: str) -> bool:
    """Return whether ``body`` already contains the monthly changelog heading.

    Args:
        body: GitHub release notes.

    Returns:
        True when a line starts with ``## Monthly Changelog Summary``.
    """
    for line in body.splitlines():
        if line.strip().startswith(MONTHLY_CHANGELOG_HEADING_PREFIX):
            return True
    return False


def split_changes(lines: list[str]) -> tuple[list[str], list[str]]:
    """Split change lines into human edits and Konflux updates.

    Args:
        lines: What's Changed bullets, oldest first.

    Returns:
        ``(human_lines, auto_lines)``. A line that contains
        ``@red-hat-konflux[bot]`` is an auto update. A later line with the
        same pull-request URL is dropped.
    """
    human_lines: list[str] = []
    auto_lines: list[str] = []
    seen_pull_requests: set[str] = set()
    for line in lines:
        pull_request = _PULL_REQUEST_URL_RE.search(line)
        if pull_request is not None:
            url = pull_request.group(0)
            if url in seen_pull_requests:
                continue
            seen_pull_requests.add(url)
        if KONFLUX_MARKER in line:
            auto_lines.append(line)
        else:
            human_lines.append(line)
    return human_lines, auto_lines


def render_monthly_changelog(
    human_lines: list[str],
    auto_lines: list[str],
    prior: Release | None,
    year: int,
    month: int,
) -> str:
    """Return the markdown block appended to a month's newest release.

    Args:
        human_lines: What's Changed bullets that are not Konflux updates.
        auto_lines: What's Changed bullets from ``@red-hat-konflux[bot]``.
        prior: Newest release of the previous month, if one exists.
        year: Calendar year of the month being summarized.
        month: Calendar month number, 1 through 12.

    Returns:
        The changelog block, including both headings and a trailing newline.
    """
    if prior is None:
        prior_line = "Prior monthly release: none"
    else:
        prior_line = f"Prior monthly release: [{prior.tag}]({prior.url})"
    blocks = [
        "---",
        monthly_changelog_heading(year, month),
        monthly_changelog_badge(year, month),
    ]
    human_block = "\n".join(human_lines)
    if human_block:
        blocks.append(human_block)
    blocks.append("")
    blocks.append(prior_line)
    blocks.append("")
    blocks.append(AUTO_UPDATES_HEADING)
    auto_block = "\n".join(auto_lines)
    if auto_block:
        blocks.append(auto_block)
    blocks.append("---")
    return "\n".join(blocks) + "\n"


def append_changelog(body: str, section: str) -> str:
    """Return ``body`` with ``section`` appended after a blank line.

    Args:
        body: Existing release notes. Empty notes get only ``section``.
        section: Monthly changelog block.

    Returns:
        The combined notes.
    """
    stripped = body.rstrip()
    if stripped:
        return f"{stripped}\n\n{section}"
    return section


def sorted_releases(releases: list[Release]) -> list[Release]:
    """Return ``releases`` from oldest to newest.

    Args:
        releases: Releases to order. May be empty.

    Returns:
        A new list. Equal timestamps are ordered by tag.

    Raises:
        ValueError: A release time has no timezone.
    """
    return sorted(releases, key=lambda release: (published_utc(release), release.tag))


def group_by_month(releases: list[Release]) -> dict[tuple[int, int], list[Release]]:
    """Group releases by their UTC publish month.

    Args:
        releases: Releases to group.

    Returns:
        A map of ``(year, month)`` to the releases published in that month.

    Raises:
        ValueError: A release time has no timezone.
    """
    grouped: dict[tuple[int, int], list[Release]] = {}
    for release in releases:
        published = published_utc(release)
        grouped.setdefault((published.year, published.month), []).append(release)
    return grouped


def _month_changes(ordered: list[Release]) -> tuple[list[str], list[str]]:
    """Return human and Konflux bullets for releases ordered oldest first.

    Args:
        ordered: One month of releases, oldest first.

    Returns:
        ``(human_lines, auto_lines)`` with duplicate pull requests removed.
    """
    lines: list[str] = []
    for release in ordered:
        lines.extend(extract_changed_lines(release.body))
    return split_changes(lines)


def _prior_release(
    grouped: dict[tuple[int, int], list[Release]],
    year: int,
    month: int,
) -> Release | None:
    """Return the newest release in the month before ``year``/``month``.

    Args:
        grouped: Releases grouped by UTC month.
        year: Year of the month being summarized.
        month: Month being summarized.

    Returns:
        The newest prior release, or None when that month has none.
    """
    ordered = sorted_releases(grouped.get(previous_month(year, month), []))
    if not ordered:
        return None
    return ordered[-1]


def releases_to_update(releases: list[Release], today: date, months: int) -> ChangelogPlan:
    """Choose release notes to edit for completed months.

    Args:
        releases: Published releases. Include the month before the window so
            the oldest changelog can link to it.
        today: Run date. The current month is not edited.
        months: How many completed months to cover.

    Returns:
        Updates for the newest release of each target month that does not
        already contain a monthly changelog, and tags left unchanged because
        that heading is already present. Months are newest first.

    Raises:
        ValueError: ``months`` is less than 1, or a release time has no timezone.
    """
    grouped = group_by_month(releases)
    updates: list[ReleaseUpdate] = []
    skipped_tags: list[str] = []
    for year, month in completed_months(today, months):
        ordered = sorted_releases(grouped.get((year, month), []))
        if not ordered:
            continue
        newest = ordered[-1]
        if already_has_changelog(newest.body):
            skipped_tags.append(newest.tag)
            continue
        human_lines, auto_lines = _month_changes(ordered)
        section = render_monthly_changelog(
            human_lines,
            auto_lines,
            _prior_release(grouped, year, month),
            year,
            month,
        )
        updates.append(ReleaseUpdate(tag=newest.tag, body=append_changelog(newest.body, section)))
    return ChangelogPlan(updates=tuple(updates), skipped_tags=tuple(skipped_tags))


def releases_api_path(repo: str, page: int) -> str:
    """Return the ``gh api`` path for one page of releases.

    Args:
        repo: ``owner/name`` repository.
        page: 1-based page number.

    Returns:
        A path and query string for ``gh api``. Pages hold ``RELEASES_PAGE_SIZE`` releases.
    """
    return f"repos/{repo}/releases?per_page={RELEASES_PAGE_SIZE}&page={page}"


def gh_json_list(path: str) -> list[dict[str, Any]]:
    """Return a JSON list from ``gh api``.

    Args:
        path: Path and query passed to ``gh api``.

    Returns:
        The parsed list of objects.

    Raises:
        RuntimeError: ``gh`` exits non-zero.
        ValueError: The response is not a JSON list of objects.
    """
    result = subprocess.run(
        ["gh", "api", path],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"gh api {path} failed: {detail}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"gh api {path} returned invalid JSON") from exc
    if not isinstance(payload, list):
        raise ValueError(f"gh api {path}: want a list, got {type(payload).__name__}")
    items: list[dict[str, Any]] = []
    for entry in payload:
        if not isinstance(entry, dict):
            raise ValueError(f"gh api {path}: want a list of objects, got {type(entry).__name__}")
        items.append(entry)
    return items


def fetch_releases(
    repo: str,
    oldest: date,
    api: Callable[[str], list[dict[str, Any]]],
) -> list[Release]:
    """Return published releases on or after ``oldest``.

    Pages are newest first. Pagination stops on a short page or on the first
    page that contains an older release, so a monthly run does not download
    the full release history.

    Args:
        repo: ``owner/name`` repository.
        oldest: First day of the earliest month that must be included.
        api: Fetches one ``gh api`` path and returns a JSON list.

    Returns:
        Releases whose publish time is on or after ``oldest``. Drafts are omitted.

    Raises:
        RuntimeError: The API call fails.
        ValueError: A published release is missing required fields.
    """
    cutoff = datetime(oldest.year, oldest.month, oldest.day, tzinfo=timezone.utc)
    collected: list[Release] = []
    page = 1
    while True:
        items = api(releases_api_path(repo, page))
        passed_cutoff = False
        for item in items:
            release = release_from_api(item)
            if release is None:
                continue
            if published_utc(release) < cutoff:
                passed_cutoff = True
                continue
            collected.append(release)
        if passed_cutoff or len(items) < RELEASES_PAGE_SIZE:
            break
        page += 1
    return collected


def edit_release_notes(repo: str, tag: str, body: str) -> None:
    """Replace the notes of ``tag`` with ``body``.

    Args:
        repo: ``owner/name`` repository.
        tag: Release tag to edit.
        body: Full notes, including the monthly changelog.

    Raises:
        RuntimeError: ``gh release edit`` exits non-zero.
    """
    result = subprocess.run(
        ["gh", "release", "edit", tag, "--repo", repo, "--notes-file", "-"],
        input=body,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"gh release edit {tag} failed: {detail}")


def print_update_body(update: ReleaseUpdate, output: TextIO) -> None:
    """Print one release's full notes for logs and dry runs.

    Args:
        update: Tag and body to print.
        output: Destination stream.
    """
    print(f"--- {update.tag} ---", file=output)
    end = "" if update.body.endswith("\n") else "\n"
    print(update.body, file=output, end=end)


def apply_changelog_plan(
    repo: str,
    plan: ChangelogPlan,
    mode: NotesWriteMode,
    edit: Callable[[str, str, str], None],
    output: TextIO,
) -> None:
    """Print or apply ``plan``.

    Args:
        repo: ``owner/name`` repository.
        plan: Releases to edit and releases already summarized.
        mode: Edit GitHub or print the notes.
        edit: Writes one release's notes. Not called for a dry run.
        output: Where progress and notes are written. In edit mode the new body
            is printed before each ``edit`` call so failed runs still show the
            payload that was sent.

    Raises:
        RuntimeError: Editing a release fails, or ``mode`` is not handled.
    """
    if not plan.updates and not plan.skipped_tags:
        print("No releases to update.", file=output)
        return
    for tag in plan.skipped_tags:
        print(f"Skipped {tag}: monthly changelog already present", file=output)
    for update in plan.updates:
        if mode is NotesWriteMode.DRY_RUN:
            print_update_body(update, output)
            continue
        if mode is NotesWriteMode.EDIT:
            print_update_body(update, output)
            edit(repo, update.tag, update.body)
            print(f"Updated {update.tag}", file=output)
            continue
        assert_never(mode)


def parse_repo(repo: str) -> str:
    """Return ``repo`` when it is ``owner/name``.

    Args:
        repo: Repository slug, usually ``GITHUB_REPOSITORY``.

    Returns:
        The same slug.

    Raises:
        ValueError: ``repo`` is not ``owner/name``.
    """
    if _REPO_RE.fullmatch(repo) is None:
        raise ValueError(f"invalid repo {repo!r}: want owner/name")
    return repo


def parse_today(value: str) -> date:
    """Return ``value`` as a calendar date.

    Args:
        value: A ``YYYY-MM-DD`` date.

    Returns:
        The parsed date.

    Raises:
        ValueError: ``value`` is not ``YYYY-MM-DD``.
    """
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"invalid today {value!r}: want YYYY-MM-DD") from exc


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Arguments after the program name.

    Returns:
        The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Append a monthly changelog to the newest GitHub release of recent months.",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=2,
        help="Completed calendar months to update (default: 2)",
    )
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY", ""),
        help="owner/name repository (default: GITHUB_REPOSITORY)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print updated notes without editing releases",
    )
    parser.add_argument(
        "--today",
        default="",
        help="Override the run date as YYYY-MM-DD in UTC (default: today)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Update monthly changelogs for the newest release of recent months."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        repo = parse_repo(args.repo)
        today = datetime.now(timezone.utc).date() if args.today == "" else parse_today(args.today)
        mode = NotesWriteMode.DRY_RUN if args.dry_run else NotesWriteMode.EDIT
        releases = fetch_releases(repo, oldest_release_date(today, args.months), gh_json_list)
        plan = releases_to_update(releases, today, args.months)
        apply_changelog_plan(repo, plan, mode, edit_release_notes, sys.stdout)
    except (ValueError, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
