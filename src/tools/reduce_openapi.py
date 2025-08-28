#!/usr/bin/env python3
"""
Reduce an OpenAPI JSON document to only include the operations and referenced schemas
for a selected set of endpoints (paths + optional methods).

Reusable API:
- class OpenAPIReducer(document: dict)
  - reduce(endpoints: Iterable[str]) -> dict
- function reduce_openapi_from_string(openapi_json: str, endpoints: Iterable[str]) -> str

CLI usage:
  python -m tools.reduce_openapi --file openapi.json --endpoint GET:/api/foo --endpoint /api/bar
  or
  python src/tools/reduce_openapi.py --file openapi.json --endpoint GET:/api/foo

Notes:
- Endpoints may be provided either as "+METHOD:+PATH" (e.g. "GET:/v1/users") or
  just "+PATH" to include all methods on that path.
- Keeps only referenced components (schemas, parameters, requestBodies, responses, headers) reachable
  from the selected operations.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import deque
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

HttpMethod = str
PathTemplate = str


class OpenAPIReducer:
    """Reduce an OpenAPI document to specific endpoints and their transitive component refs."""

    def __init__(self, document: Dict[str, Any]) -> None:
        self.document = document

    @classmethod
    def from_response(cls, response: Dict[str, Any] | str) -> "OpenAPIReducer":
        """Create a reducer from a dict or a JSON string response."""
        if isinstance(response, dict):
            return cls(response)
        if isinstance(response, str):
            return cls(json.loads(response))
        raise TypeError("OpenAPIReducer.from_response expects a dict or JSON string")

    @staticmethod
    def parse_endpoint_spec(spec: str) -> Tuple[Optional[HttpMethod], PathTemplate]:
        """Parse an endpoint spec like "GET:/v1/users" or "/v1/users".

        Returns (method_or_None, path)
        """
        if ":" in spec:
            method, path = spec.split(":", 1)
            method = method.strip().lower()
            return method, path.strip()
        return None, spec.strip()

    @staticmethod
    def _is_operation_method(key: str) -> bool:
        return key.lower() in {
            "get",
            "put",
            "post",
            "delete",
            "options",
            "head",
            "patch",
            "trace",
        }

    @staticmethod
    def _collect_component_refs(node: Any) -> Set[Tuple[str, str]]:
        """Walk a node and collect $ref values to components.

        Returns a set of (component_type, name) like ("schemas", "User").
        Covers refs in parameters, requestBody, responses, callbacks, and nested schemas.
        """
        refs: Set[Tuple[str, str]] = set()

        def visit(n: Any) -> None:
            if isinstance(n, dict):
                if "$ref" in n and isinstance(n["$ref"], str):
                    ref = n["$ref"]
                    m = re.match(r"^#\/components\/([^\/]+)\/(.+)$", ref)
                    if m:
                        refs.add((m.group(1), m.group(2)))
                for v in n.values():
                    visit(v)
            elif isinstance(n, list):
                for v in n:
                    visit(v)

        visit(node)
        return refs

    @staticmethod
    def _resolve_schema_refs(components: Dict[str, Any], initial_refs: Set[Tuple[str, str]]) -> Set[Tuple[str, str]]:
        """Expand schema refs transitively within components to include everything needed."""
        visited: Set[Tuple[str, str]] = set()
        queue: deque[Tuple[str, str]] = deque(initial_refs)

        def visit_component_value(value: Any) -> None:
            if isinstance(value, dict):
                if "$ref" in value and isinstance(value["$ref"], str):
                    ref = value["$ref"]
                    m = re.match(r"^#\/components\/([^\/]+)\/(.+)$", ref)
                    if m:
                        queue.append((m.group(1), m.group(2)))
                for v in value.values():
                    visit_component_value(v)
            elif isinstance(value, list):
                for v in value:
                    visit_component_value(v)

        while queue:
            comp_type, name = queue.popleft()
            if (comp_type, name) in visited:
                continue
            visited.add((comp_type, name))
            comp_bucket = components.get(comp_type)
            if not isinstance(comp_bucket, dict):
                continue
            comp_value = comp_bucket.get(name)
            if comp_value is None:
                continue
            visit_component_value(comp_value)

        return visited

    def _get_selected_methods_for_path(
        self, path: str, path_item: Dict[str, Any], endpoint_specs: List[Tuple[Optional[str], str]]
    ) -> Set[str]:
        """Determine which HTTP methods are selected for a given path."""
        path_selected_methods: Set[str] = set()
        for method, path_template in endpoint_specs:
            if path_template == path:
                if method is None:
                    path_selected_methods = {k for k in path_item.keys() if self._is_operation_method(k)}
                else:
                    path_selected_methods.add(method)
        return path_selected_methods

    def _build_path_item(self, path_item: Dict[str, Any], selected_methods: Set[str]) -> Dict[str, Any]:
        """Build a new path item with only selected methods and non-operation fields."""
        new_path_item: Dict[str, Any] = {}

        # Copy over non-operation fields (summary, description, servers, parameters, etc.)
        for key, value in path_item.items():
            if not self._is_operation_method(key):
                new_path_item[key] = value

        # Copy selected methods
        for method in selected_methods:
            op = path_item.get(method)
            if isinstance(op, dict):
                new_path_item[method] = op

        return new_path_item

    def _collect_security_schemes(self, operation: Dict[str, Any]) -> Set[str]:
        """Collect security scheme names from an operation's security requirements."""
        schemes: Set[str] = set()
        op_security = operation.get("security")
        if isinstance(op_security, list):
            for req in op_security:
                if isinstance(req, dict):
                    for scheme in req.keys():
                        schemes.add(str(scheme))
        return schemes

    def _build_reduced_paths(
        self, original_paths: Dict[str, Any], endpoint_specs: List[Tuple[Optional[str], str]]
    ) -> Tuple[Dict[str, Any], Set[Tuple[str, str]], Set[str]]:
        """Build reduced paths and collect operation refs and security schemes."""
        reduced_paths: Dict[str, Any] = {}
        operation_refs: Set[Tuple[str, str]] = set()
        needed_security_schemes: Set[str] = set()

        for path, path_item in original_paths.items():
            if not isinstance(path_item, dict):
                continue

            selected_methods = self._get_selected_methods_for_path(path, path_item, endpoint_specs)
            if not selected_methods:
                continue

            new_path_item = self._build_path_item(path_item, selected_methods)

            # Collect refs from path-level fields
            if new_path_item:
                operation_refs |= self._collect_component_refs(new_path_item)

            # Collect refs and security schemes from operations
            for method in selected_methods:
                op = path_item.get(method)
                if isinstance(op, dict):
                    operation_refs |= self._collect_component_refs(op)
                    needed_security_schemes |= self._collect_security_schemes(op)

            if new_path_item:
                reduced_paths[path] = new_path_item

        return reduced_paths, operation_refs, needed_security_schemes

    def _build_base_document(self, data: Dict[str, Any], reduced_paths: Dict[str, Any]) -> Dict[str, Any]:
        """Build the base document with standard OpenAPI fields and reduced paths."""
        new_doc: Dict[str, Any] = {}

        # Copy standard OpenAPI fields
        for key in ["openapi", "info", "servers", "tags", "externalDocs", "security"]:
            if key in data:
                new_doc[key] = data[key]

        new_doc["paths"] = reduced_paths
        return new_doc

    def _collect_top_level_security_schemes(self, data: Dict[str, Any]) -> Set[str]:
        """Collect security scheme names from top-level security requirements."""
        schemes: Set[str] = set()
        top_security = data.get("security")
        if isinstance(top_security, list):
            for req in top_security:
                if isinstance(req, dict):
                    for scheme in req.keys():
                        schemes.add(str(scheme))
        return schemes

    def _build_pruned_components(self, components: Dict[str, Any], needed_refs: Set[Tuple[str, str]]) -> Dict[str, Any]:
        """Build pruned components containing only needed references."""
        pruned_components: Dict[str, Any] = {}

        for comp_type, comp_bucket in components.items():
            if not isinstance(comp_bucket, dict):
                continue
            kept: Dict[str, Any] = {}
            for name, value in comp_bucket.items():
                if (comp_type, name) in needed_refs:
                    kept[name] = value
            if kept:
                pruned_components[comp_type] = kept

        return pruned_components

    def reduce(self, endpoints: Iterable[str]) -> Dict[str, Any]:
        """Reduce the OpenAPI document to only include specified endpoints and their dependencies.

        Args:
            endpoints: Iterable of endpoint specifications like "GET:/api/users" or "/api/users"

        Returns:
            A new OpenAPI document containing only the specified endpoints and their dependencies
        """
        data = self.document

        # Validate input
        original_paths = data.get("paths", {})
        if not isinstance(original_paths, dict):
            raise ValueError("Invalid OpenAPI: paths must be an object")

        endpoint_specs = [self.parse_endpoint_spec(e) for e in endpoints]

        # Build reduced paths and collect references
        reduced_paths, operation_refs, needed_security_schemes = self._build_reduced_paths(
            original_paths, endpoint_specs
        )

        # Build base document
        new_doc = self._build_base_document(data, reduced_paths)

        # Handle components
        components = data.get("components", {})
        if not isinstance(components, dict):
            components = {}

        # Add top-level security schemes
        needed_security_schemes |= self._collect_top_level_security_schemes(data)

        # Add security schemes to operation refs
        for scheme in needed_security_schemes:
            operation_refs.add(("securitySchemes", scheme))

        # Resolve transitive references
        needed_refs = self._resolve_schema_refs(components, operation_refs)

        # Add pruned components if any are needed
        pruned_components = self._build_pruned_components(components, needed_refs)
        if pruned_components:
            new_doc["components"] = pruned_components

        return new_doc


def reduce_openapi_from_string(openapi_json: str, endpoints: Iterable[str]) -> str:
    """Reduce an OpenAPI JSON string to only include specified endpoints.

    Args:
        openapi_json: OpenAPI specification as a JSON string
        endpoints: Iterable of endpoint specifications like "GET:/api/users" or "/api/users"

    Returns:
        Reduced OpenAPI specification as a formatted JSON string
    """
    data = json.loads(openapi_json)
    reducer = OpenAPIReducer(data)
    reduced = reducer.reduce(endpoints)
    return json.dumps(reduced, indent=2, sort_keys=False, ensure_ascii=False) + "\n"


def _read_file_bytes(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def main(argv: Optional[Iterable[str]] = None) -> int:
    """Main CLI entry point for reducing OpenAPI specifications.

    Args:
        argv: Command line arguments (uses sys.argv if None)

    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    parser = argparse.ArgumentParser(description="Reduce OpenAPI spec to selected endpoints")
    parser.add_argument("--file", required=True, help="Path to openapi.json")
    parser.add_argument(
        "--endpoint",
        action="append",
        default=[],
        help="Endpoint spec like GET:/v1/users or /v1/users (repeatable)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if not args.endpoint:
        print("No endpoints provided. Nothing to do.", file=sys.stderr)
        return 2

    raw = _read_file_bytes(args.file)
    original_str = raw.decode("utf-8")

    reduced_str = reduce_openapi_from_string(original_str, args.endpoint)

    # Output reduced doc
    sys.stdout.write(reduced_str)

    # Print stats to stderr
    before_len = len(json.dumps(json.loads(original_str), indent=2, ensure_ascii=False))
    after_len = len(reduced_str)
    print(
        (
            f"\n--- Stats ---\n"
            f"Before (pretty chars): {before_len}\n"
            f"After  (pretty chars): {after_len}\n"
            f"Delta               : {before_len - after_len}"
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
