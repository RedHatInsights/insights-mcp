"""Tests for reducing Image Builder OpenAPI to POST:/blueprints.

This verifies that the reducer keeps only the components referenced by
the selected endpoint and removes unrelated ones. It also checks that
the reduced spec is smaller than the original.
"""

from __future__ import annotations

import json

import httpx
import pytest

from tools.reduce_openapi import OpenAPIReducer


@pytest.mark.parametrize("endpoint_spec", ["POST:/blueprints"])
def test_reduce_openapi_for_post_blueprints(verbose_logger, endpoint_spec: str):
    # Download the live Image Builder OpenAPI (does not require authentication)
    url = "https://console.redhat.com/api/image-builder/v1/openapi.json"
    response = httpx.get(url, timeout=60)
    response.raise_for_status()
    original_doc = response.json()

    # Basic sanity
    assert "paths" in original_doc and isinstance(original_doc["paths"], dict)
    assert "components" in original_doc and isinstance(original_doc["components"], dict)

    # Run reducer
    reducer = OpenAPIReducer.from_response(original_doc)
    reduced_doc = reducer.reduce([endpoint_spec])

    # Print a diff of schema keys (for visibility in test output)
    original_components = original_doc.get("components", {})
    reduced_components = reduced_doc.get("components", {})

    original_schemas = original_components.get("schemas", {}) if isinstance(original_components, dict) else {}
    reduced_schemas = reduced_components.get("schemas", {}) if isinstance(reduced_components, dict) else {}

    original_schema_keys = set(original_schemas.keys()) if isinstance(original_schemas, dict) else set()
    reduced_schema_keys = set(reduced_schemas.keys()) if isinstance(reduced_schemas, dict) else set()

    kept_keys = sorted(original_schema_keys & reduced_schema_keys)
    removed_keys = sorted(original_schema_keys - reduced_schema_keys)
    added_keys = sorted(reduced_schema_keys - original_schema_keys)

    def sample(items: list[str], limit: int = 25) -> list[str]:
        return items[:limit]

    verbose_logger.info(
        (
            f"[DEBUG] schema keys original={len(original_schema_keys)} "
            f"reduced={len(reduced_schema_keys)} kept={len(kept_keys)} "
            f"removed={len(removed_keys)} added={len(added_keys)}"
        )
    )
    verbose_logger.info(f"[DEBUG] kept sample: {sample(kept_keys)}")
    verbose_logger.info(f"[DEBUG] removed sample: {sample(removed_keys)}")
    verbose_logger.info(f"[DEBUG] added sample: {sample(added_keys)}")

    # Assert reduced size smaller than original (pretty-printed length proxy)
    original_len = len(json.dumps(original_doc, indent=2, ensure_ascii=False))
    reduced_len = len(json.dumps(reduced_doc, indent=2, ensure_ascii=False))
    assert reduced_len < original_len, f"Reduced spec should be smaller. original={original_len}, reduced={reduced_len}"

    # Presence: a couple of representative components should remain
    components = reduced_doc.get("components", {})
    schemas = components.get("schemas", {}) if isinstance(components, dict) else {}

    # Example of expected-to-exist schema referenced by POST /blueprints flow
    assert "CustomRepository" in schemas, "Expected CustomRepository schema to be present in reduced spec"

    # Absence: a schema that should not be needed for POST /blueprints
    assert "CloneStatusResponse" not in schemas, "CloneStatusResponse should be pruned for POST:/blueprints"

    # Paths should only include the selected path/method
    assert "/blueprints" in reduced_doc["paths"], "Reduced spec must include /blueprints path"
    path_item = reduced_doc["paths"]["/blueprints"]
    assert "post" in path_item and isinstance(path_item["post"], dict), "POST operation must remain"
