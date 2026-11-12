"""Planning API routes backed by the canonical LLM-test catalog."""

# pylint: disable=duplicate-code

from __future__ import annotations

from collections.abc import Callable, Iterable
from http import HTTPMethod
from typing import Any

from tests.mock_insights_api.catalog import DEFAULT_CATALOG
from tests.mock_insights_api.catalog.models import (
    ApplicationStreamRecord,
    Host,
    MockCatalog,
    RHELLifecycleRecord,
    UpcomingChange,
)
from tests.mock_insights_api.registry import MockInsightsAPI
from tests.mock_insights_api.routes.query import query_bool, query_int, query_text
from tests.mock_insights_api.types import MockRequest, MockResponse


def _meta_response(records: list[dict[str, Any]]) -> MockResponse:
    return MockResponse(body={"meta": {"count": len(records), "total": len(records)}, "data": records})


def _system_detail(host: Host) -> dict[str, Any]:
    major, _, minor = host.rhel_version.partition(".")
    return {
        "id": host.id,
        "display_name": host.hostname,
        "os_major": int(major),
        "os_minor": int(minor or 0),
    }


def _hosts_for_version(catalog: MockCatalog, request: MockRequest) -> tuple[Host, ...]:
    major = query_int(request, "major", None)
    minor = query_int(request, "minor", None)
    hosts: list[Host] = []
    for host in catalog.hosts:
        host_major, _, host_minor = host.rhel_version.partition(".")
        if major is not None and int(host_major) != major:
            continue
        if minor is not None and int(host_minor or 0) != minor:
            continue
        hosts.append(host)
    return tuple(hosts)


def _rhel_record(record: RHELLifecycleRecord) -> dict[str, Any]:
    return {
        "name": record.name,
        "start_date": record.start_date,
        "end_date": record.end_date,
        "support_status": record.support_status,
        "display_name": record.display_name,
        "major": record.major,
        "minor": record.minor,
        "end_date_e4s": record.end_date_e4s,
        "end_date_els": record.end_date_els,
        "end_date_eus": record.end_date_eus,
    }


def _rhel_lifecycle_response(catalog: MockCatalog) -> dict[str, Any]:
    return {"data": [_rhel_record(record) for record in catalog.rhel_lifecycle]}


def _relevant_rhel_records(
    catalog: MockCatalog, request: MockRequest
) -> list[tuple[RHELLifecycleRecord, tuple[Host, ...], bool]]:
    hosts = _hosts_for_version(catalog, request)
    observed_versions = {host.rhel_version for host in hosts}
    major = query_int(request, "major", None)
    minor = query_int(request, "minor", None)
    include_related = query_bool(request, "related", False)
    records: list[tuple[RHELLifecycleRecord, tuple[Host, ...], bool]] = []

    for record in catalog.rhel_lifecycle:
        version = f"{record.major}.{record.minor}" if record.minor is not None else str(record.major)
        if version in observed_versions:
            records.append((record, tuple(host for host in hosts if host.rhel_version == version), False))
            continue
        if not include_related or major is not None and record.major != major:
            continue
        if minor is not None and (record.minor is None or record.minor < minor):
            continue
        records.append((record, (), True))
    return records


def _relevant_rhel_response(catalog: MockCatalog, request: MockRequest) -> MockResponse:
    records = []
    for record, hosts, related in _relevant_rhel_records(catalog, request):
        systems = [_system_detail(host) for host in hosts]
        records.append(
            {
                "name": record.name,
                "display_name": record.display_name,
                "major": record.major,
                "minor": record.minor,
                "start_date": record.start_date,
                "end_date": record.end_date,
                "support_status": record.support_status,
                "count": len(hosts),
                "lifecycle_type": "mainline",
                "related": related,
                "systems_detail": systems,
                "systems": [system["id"] for system in systems],
            }
        )
    return _meta_response(records)


def _stream_record(record: ApplicationStreamRecord) -> dict[str, Any]:
    return {
        "name": record.name,
        "display_name": record.display_name,
        "application_stream_name": record.application_stream_name,
        "application_stream_type": record.application_stream_type,
        "stream": record.stream,
        "start_date": record.start_date,
        "end_date": record.end_date,
        "impl": record.impl,
        "initial_product_version": record.initial_product_version,
        "support_status": record.support_status,
        "os_major": record.os_major,
        "os_minor": record.os_minor,
        "lifecycle": record.lifecycle,
        "rolling": record.rolling,
    }


def _stream_matches(record: ApplicationStreamRecord, request: MockRequest) -> bool:
    filters = (
        ("name", record.name),
        ("application_stream_name", record.application_stream_name),
        ("application_stream_type", record.application_stream_type or ""),
    )
    for parameter, value in filters:
        query = query_text(request, parameter).casefold()
        if query and query not in value.casefold():
            return False

    for parameter in ("kind",):
        query = query_text(request, parameter).casefold()
        if not query:
            continue
        implementation = record.impl.casefold()
        if query == "module":
            query = "dnf_module"
        if query == "package":
            query = "package"
        if query != implementation:
            return False
    return True


def _appstreams_response(records: Iterable[ApplicationStreamRecord]) -> MockResponse:
    return _meta_response([_stream_record(record) for record in records])


def _raw_appstreams_response(catalog: MockCatalog, request: MockRequest, major: int) -> MockResponse:
    records = (
        record
        for record in catalog.application_streams
        if record.os_major == major and _stream_matches(record, request)
    )
    return _appstreams_response(records)


def _all_appstreams_response(catalog: MockCatalog, request: MockRequest) -> MockResponse:
    return _appstreams_response(record for record in catalog.application_streams if _stream_matches(record, request))


def _installed_stream_hosts(
    catalog: MockCatalog, record: ApplicationStreamRecord, request: MockRequest
) -> tuple[Host, ...]:
    hosts = _hosts_for_version(catalog, request)
    stream_key = f"{record.name}:{record.stream}"
    return tuple(
        host
        for host in hosts
        if stream_key in catalog.profile_for_host(host.id).installed_app_streams
        and host.rhel_version.split(".", 1)[0] == str(record.os_major)
    )


def _stream_number(stream: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(part) for part in stream.split("."))
    except ValueError:
        return None


def _is_successor(candidate: ApplicationStreamRecord, installed: ApplicationStreamRecord) -> bool:
    if candidate.application_stream_name != installed.application_stream_name:
        return False
    if (
        candidate.os_major != installed.os_major
        or candidate.name == installed.name
        and candidate.stream == installed.stream
    ):
        return False
    candidate_number = _stream_number(candidate.stream)
    installed_number = _stream_number(installed.stream)
    return candidate_number is not None and installed_number is not None and candidate_number > installed_number


def _relevant_stream_records(
    catalog: MockCatalog, request: MockRequest
) -> list[tuple[ApplicationStreamRecord, tuple[Host, ...], bool]]:
    installed: list[tuple[ApplicationStreamRecord, tuple[Host, ...]]] = []
    for record in catalog.application_streams:
        hosts = _installed_stream_hosts(catalog, record, request)
        if hosts:
            installed.append((record, hosts))

    records: list[tuple[ApplicationStreamRecord, tuple[Host, ...], bool]] = [
        (record, hosts, False) for record, hosts in installed
    ]
    if query_bool(request, "related", True):
        for installed_record, _ in installed:
            records.extend(
                (candidate, (), True)
                for candidate in catalog.application_streams
                if _is_successor(candidate, installed_record)
                and all(existing[0] != candidate or not existing[2] for existing in records)
            )
    return records


def _relevant_stream_response(catalog: MockCatalog, request: MockRequest) -> MockResponse:
    records = []
    for record, hosts, related in _relevant_stream_records(catalog, request):
        systems = [_system_detail(host) for host in hosts]
        records.append(
            {
                **_stream_record(record),
                "count": len(hosts),
                "systems_detail": systems,
                "systems": [system["id"] for system in systems],
                "related": related,
            }
        )
    return _meta_response(records)


def _change_hosts(catalog: MockCatalog, change: UpcomingChange, request: MockRequest) -> tuple[Host, ...]:
    hosts = _hosts_for_version(catalog, request)
    return tuple(
        host
        for host in hosts
        if host.rhel_version.split(".", 1)[0] == str(change.os_major)
        and set(change.packages).intersection(catalog.profile_for_host(host.id).installed_packages)
    )


def _change_record(change: UpcomingChange, hosts: tuple[Host, ...] | None = None) -> dict[str, Any]:
    systems = [_system_detail(host) for host in hosts or ()]
    details: dict[str, Any] = {
        "architecture": change.architecture,
        "detailFormat": 0,
        "summary": change.summary,
        "trainingTicket": change.training_ticket,
        "dateAdded": change.date_added,
        "lastModified": change.last_modified,
        "deployedDate": change.deployed_date,
    }
    if hosts is not None:
        details.update(
            {
                "potentiallyAffectedSystemsCount": len(systems),
                "potentiallyAffectedSystemsDetail": systems,
                "potentiallyAffectedSystems": [system["id"] for system in systems],
            }
        )
    return {
        "name": change.name,
        "type": change.change_type,
        "packages": list(change.packages),
        "release": change.release,
        "os_major": change.os_major,
        "date": change.date,
        "details": details,
        "package": change.packages[0] if change.packages else "",
    }


def _upcoming_response(catalog: MockCatalog) -> dict[str, Any]:
    return _meta_response([_change_record(change) for change in catalog.upcoming_changes]).body


def _relevant_upcoming_response(catalog: MockCatalog, request: MockRequest) -> MockResponse:
    records = []
    for change in catalog.upcoming_changes:
        hosts = _change_hosts(catalog, change, request)
        if hosts:
            records.append(_change_record(change, hosts))
    return _meta_response(records)


def _raw_appstreams_factory(catalog: MockCatalog, major: int) -> Callable[[MockRequest], MockResponse]:
    def factory(request: MockRequest) -> MockResponse:
        return _raw_appstreams_response(catalog, request, major)

    return factory


def register_planning_routes(
    api: MockInsightsAPI,
    catalog: MockCatalog = DEFAULT_CATALOG,
    *,
    api_path: str = "api/roadmap/v1",
) -> None:
    """Register the Planning endpoints exercised by current LLM scenarios."""
    api.register(
        HTTPMethod.GET,
        f"{api_path}/upcoming-changes",
        response_body=_upcoming_response(catalog),
    )
    api.register(
        HTTPMethod.GET,
        f"{api_path}/relevant/upcoming-changes",
        response_factory=lambda request: _relevant_upcoming_response(catalog, request),
    )
    api.register(
        HTTPMethod.GET,
        f"{api_path}/lifecycle/rhel",
        response_body=_rhel_lifecycle_response(catalog),
    )
    api.register(
        HTTPMethod.GET,
        f"{api_path}/relevant/lifecycle/rhel",
        response_factory=lambda request: _relevant_rhel_response(catalog, request),
    )
    api.register(
        HTTPMethod.GET,
        f"{api_path}/lifecycle/app-streams/streams",
        response_factory=lambda request: _all_appstreams_response(catalog, request),
    )
    for major in sorted({record.os_major for record in catalog.application_streams if record.os_major is not None}):
        api.register(
            HTTPMethod.GET,
            f"{api_path}/lifecycle/app-streams/{major}",
            response_factory=_raw_appstreams_factory(catalog, major),
        )
    api.register(
        HTTPMethod.GET,
        f"{api_path}/relevant/lifecycle/app-streams",
        response_factory=lambda request: _relevant_stream_response(catalog, request),
    )
