"""Fetch and validate OpenAPI documents used by the Insights mock."""

from __future__ import annotations

import json
from typing import Any
from urllib.request import urlopen

_OPENAPI_SOURCES = {
    "image_builder": "https://console.redhat.com/api/image-builder/v1/openapi.json",
    "vulnerability": "https://console.redhat.com/api/vulnerability/v1/openapi.json",
}


def _validate_openapi_document(service: str, document: Any) -> dict[str, Any]:
    if not isinstance(document, dict) or not isinstance(document.get("paths"), dict):
        raise ValueError(f"Invalid OpenAPI document for {service}")
    return document


def fetch_openapi_document(service: str) -> dict[str, Any]:
    """Fetch and validate the current public OpenAPI document for a service."""
    try:
        url = _OPENAPI_SOURCES[service]
    except KeyError as error:
        raise ValueError(f"No OpenAPI source configured for {service}") from error

    with urlopen(url, timeout=60) as response:
        return _validate_openapi_document(service, json.load(response))


def fetch_openapi_documents() -> dict[str, dict[str, Any]]:
    """Fetch the OpenAPI documents needed by the mock before it starts."""
    return {service: fetch_openapi_document(service) for service in _OPENAPI_SOURCES}
