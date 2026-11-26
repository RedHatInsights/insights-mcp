"""Image Builder read routes backed by the canonical LLM-test catalog."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import partial
from http import HTTPMethod
from typing import Any
from uuid import uuid4

from tests.mock_insights_api.catalog import DEFAULT_CATALOG
from tests.mock_insights_api.catalog.models import ImageBlueprint, ImageCompose, MockCatalog
from tests.mock_insights_api.openapi import fetch_openapi_document
from tests.mock_insights_api.registry import MockInsightsAPI
from tests.mock_insights_api.routes.pagination import page_params
from tests.mock_insights_api.routes.request import request_body
from tests.mock_insights_api.types import MockRequest, MockResponse


@dataclass(slots=True)
class _ImageBuilderState:
    """Mutable Image Builder resources owned by one mock API instance."""

    blueprints: list[ImageBlueprint]
    composes: list[ImageCompose]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _find_blueprint(state: _ImageBuilderState, blueprint_id: str) -> ImageBlueprint:
    return next(blueprint for blueprint in state.blueprints if blueprint.id == blueprint_id)


def _find_compose(state: _ImageBuilderState, compose_id: str) -> ImageCompose:
    return next(compose for compose in state.composes if compose.id == compose_id)


def _blueprint_from_body(
    body: Mapping[str, Any],
    blueprint_id: str,
    current: ImageBlueprint | None = None,
) -> ImageBlueprint:
    image_requests_value = body.get("image_requests", current.image_requests if current else ())
    image_requests = (
        tuple(dict(item) for item in image_requests_value if isinstance(item, Mapping))
        if isinstance(image_requests_value, list)
        else ()
    )
    customizations_value = body.get("customizations", current.customizations if current else {})
    customizations = dict(customizations_value) if isinstance(customizations_value, Mapping) else {}
    return ImageBlueprint(
        id=blueprint_id,
        name=str(body.get("name", current.name if current else "")),
        description=str(body.get("description", current.description if current else "")),
        distribution=str(body.get("distribution", current.distribution if current else "")),
        version=current.version + 1 if current else 1,
        last_modified_at=_now(),
        image_requests=image_requests,
        customizations=customizations,
        lint={"errors": [], "warnings": []},
    )


def _blueprint_summary(blueprint: ImageBlueprint) -> dict[str, Any]:
    return {
        "description": blueprint.description,
        "id": blueprint.id,
        "last_modified_at": blueprint.last_modified_at,
        "name": blueprint.name,
        "version": blueprint.version,
    }


def _blueprint_detail(blueprint: ImageBlueprint) -> dict[str, Any]:
    return {
        **_blueprint_summary(blueprint),
        "distribution": blueprint.distribution,
        "image_requests": [dict(request) for request in blueprint.image_requests],
        "customizations": dict(blueprint.customizations),
        "lint": dict(blueprint.lint),
    }


def _compose_summary(compose: ImageCompose) -> dict[str, Any]:
    return {
        "id": compose.id,
        "blueprint_id": compose.blueprint_id,
        "image_name": compose.image_name,
        "created_at": compose.created_at,
        "request": dict(compose.request),
    }


def _compose_detail(compose: ImageCompose) -> dict[str, Any]:
    return {**_compose_summary(compose), "image_status": dict(compose.image_status)}


def _list_response(records: list[dict[str, Any]], request: MockRequest, path: str) -> MockResponse:
    offset, limit = page_params(request, 100)
    end = offset + limit
    page = records[offset:end]
    return MockResponse(
        body={
            "meta": {"count": len(page)},
            "links": {"first": path, "last": path},
            "data": page,
        }
    )


def _blueprints_response(state: _ImageBuilderState, request: MockRequest, path: str) -> MockResponse:
    records = sorted(state.blueprints, key=lambda item: item.last_modified_at, reverse=True)
    return _list_response([_blueprint_summary(blueprint) for blueprint in records], request, path)


def _composes_response(state: _ImageBuilderState, request: MockRequest, path: str) -> MockResponse:
    records = sorted(state.composes, key=lambda item: item.created_at, reverse=True)
    return _list_response([_compose_summary(compose) for compose in records], request, path)


def _blueprint_detail_response(state: _ImageBuilderState, blueprint_id: str, request: MockRequest) -> MockResponse:
    del request
    return MockResponse(body=_blueprint_detail(_find_blueprint(state, blueprint_id)))


def _compose_detail_response(state: _ImageBuilderState, compose_id: str, request: MockRequest) -> MockResponse:
    del request
    return MockResponse(body=_compose_detail(_find_compose(state, compose_id)))


def _create_blueprint_response(
    state: _ImageBuilderState,
    api: MockInsightsAPI,
    api_path: str,
    request: MockRequest,
) -> MockResponse:
    blueprint = _blueprint_from_body(request_body(request), str(uuid4()))
    state.blueprints.append(blueprint)
    _register_blueprint_routes(api, state, blueprint, api_path)
    return MockResponse(body={"id": blueprint.id}, status=201)


def _update_blueprint_response(
    state: _ImageBuilderState,
    blueprint_id: str,
    request: MockRequest,
) -> MockResponse:
    current = _find_blueprint(state, blueprint_id)
    updated = _blueprint_from_body(request_body(request), blueprint_id, current)
    state.blueprints[state.blueprints.index(current)] = updated
    return MockResponse(body={"id": updated.id})


def _compose_blueprint_response(
    state: _ImageBuilderState,
    api: MockInsightsAPI,
    api_path: str,
    blueprint_id: str,
    request: MockRequest,
) -> MockResponse:
    del request
    blueprint = _find_blueprint(state, blueprint_id)
    image_name = f"{blueprint.name}-compose"
    compose_request = {
        "distribution": blueprint.distribution,
        "image_name": image_name,
        "image_requests": [dict(item) for item in blueprint.image_requests],
        "customizations": dict(blueprint.customizations),
    }
    compose = ImageCompose(
        id=str(uuid4()),
        blueprint_id=blueprint.id,
        image_name=image_name,
        created_at=_now(),
        request=compose_request,
        image_status={"status": "pending"},
    )
    state.composes.append(compose)
    _register_compose_route(api, state, compose, api_path)
    return MockResponse(
        body=[{"id": compose.id, "blueprint_id": compose.blueprint_id, "status": "PENDING"}],
        status=202,
    )


def _register_compose_route(
    api: MockInsightsAPI,
    state: _ImageBuilderState,
    compose: ImageCompose,
    api_path: str,
) -> None:
    api.register(
        HTTPMethod.GET,
        f"{api_path}/composes/{compose.id}",
        response_factory=partial(_compose_detail_response, state, compose.id),
    )


def _register_blueprint_routes(
    api: MockInsightsAPI,
    state: _ImageBuilderState,
    blueprint: ImageBlueprint,
    api_path: str,
) -> None:
    blueprint_path = f"{api_path}/blueprints/{blueprint.id}"
    api.register(
        HTTPMethod.GET,
        blueprint_path,
        response_factory=partial(_blueprint_detail_response, state, blueprint.id),
    )
    api.register(
        HTTPMethod.PUT,
        blueprint_path,
        response_factory=partial(_update_blueprint_response, state, blueprint.id),
    )
    api.register(
        HTTPMethod.POST,
        f"{blueprint_path}/compose",
        response_factory=partial(_compose_blueprint_response, state, api, api_path, blueprint.id),
    )


def register_image_builder_routes(
    api: MockInsightsAPI,
    catalog: MockCatalog = DEFAULT_CATALOG,
    *,
    api_path: str = "api/image-builder/v1",
    openapi: Mapping[str, Any] | None = None,
) -> None:
    """Register Image Builder endpoints exercised by the LLM scenarios."""
    state = _ImageBuilderState(list(catalog.image_blueprints), list(catalog.image_composes))
    openapi_document = openapi if openapi is not None else fetch_openapi_document("image_builder")
    api.register(HTTPMethod.GET, f"{api_path}/openapi.json", response_body=openapi_document)
    api.register(
        HTTPMethod.GET,
        f"{api_path}/distributions",
        response_body=[{"name": item.name, "description": item.description} for item in catalog.image_distributions],
    )
    api.register(
        HTTPMethod.GET,
        f"{api_path}/blueprints",
        response_factory=lambda request: _blueprints_response(state, request, f"{api_path}/blueprints"),
    )
    api.register(
        HTTPMethod.GET,
        f"{api_path}/composes",
        response_factory=lambda request: _composes_response(state, request, f"{api_path}/composes"),
    )
    api.register(
        HTTPMethod.POST,
        f"{api_path}/blueprints",
        response_factory=lambda request: _create_blueprint_response(state, api, api_path, request),
    )
    for blueprint in state.blueprints:
        _register_blueprint_routes(api, state, blueprint, api_path)
    for compose in state.composes:
        _register_compose_route(api, state, compose, api_path)
