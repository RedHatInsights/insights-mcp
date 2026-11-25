# Mock Insights API for LLM tests

The mock Insights API gives the LLM tests a deterministic Insights backend. It
keeps the tests fast and repeatable, and lets them run without a configured
Insights account or live Insights data.

The mock is intentionally limited to the endpoints currently accessed by the
LLM tool scenarios. It is not a replacement for the complete Insights API.
When a tool starts using another endpoint, add that endpoint to the mock as
part of the tool change.

## Running the LLM tests

The mock API is the default backend:

```bash
make test-llm
```

The backend can be selected explicitly with `INSIGHTS_LLM_API_MODE`:

```bash
# Deterministic local catalog; this is the default.
INSIGHTS_LLM_API_MODE=mock make test-llm

# Real Insights API; useful for nightly or weekly validation.
INSIGHTS_LLM_API_MODE=live make test-llm
```

Both modes still require the configured model and guardian model endpoints.
Mock mode removes the Insights API dependency only. Live mode also requires
the Insights credentials and network access used by the live discovery
fixture. The mode accepts only `mock` and `live`.

The mock backend is selected in
[`tests/mcp_llm_eval/api_fixtures.py`](../mcp_llm_eval/api_fixtures.py). In
mock mode it starts `MockInsightsHTTPServer`, points the MCP process at
that server with `INSIGHTS_BASE_URL`, and supplies placeholder values from the
same catalog. In live mode no mock server is started and the existing live API
discovery is used instead.

## Architecture

The data flow is:

```text
MockCatalog
    -> route projections
    -> MockInsightsAPI registry
    -> MockInsightsHTTPServer
    -> InsightsClient used by the MCP toolset
    -> LLM test scenario
```

The layers have separate responsibilities:

- `catalog/` contains typed, reusable entities and the canonical synthetic
  data set.
- `routes/` translates catalog entities into the response shape expected by a
  real service endpoint. Each route module owns one service projection.
- `registry.py` provides exact method/path route registration and request
  recording. An unregistered endpoint fails instead of silently returning a
  fabricated response.
- `server.py` exposes the registry through local HTTP so the normal
  `InsightsClient` and MCP process path are exercised.
- `mcp_llm_eval/api_fixtures.py` selects mock or live mode for LLM tests.

The route registry is reusable outside the LLM tests as well:

```python
from tests.mock_insights_api import MockInsightsHTTPServer, create_mock_insights_api
from tests.mock_insights_api.openapi import fetch_openapi_documents

with MockInsightsHTTPServer(create_mock_insights_api(openapi_documents=fetch_openapi_documents())) as server:
    # Configure the client under test with server.base_url.
    ...
```

## Catalog and relationships

`DEFAULT_CATALOG` in `catalog/data.py` is the single source of mock entities.
The records are synthetic, but their relationships are intentional and must
agree across service projections.

| Relationship | Used by |
| --- | --- |
| Hosts and system profiles | Inventory host details and system profiles |
| Hosts, workspaces, and tags | Inventory groups, host filters, and prompt context |
| Hosts, CVE records, and Advisor rules | Vulnerability, Advisor, and Remediations |
| Hosts and enabled repositories | Inventory profiles and Content Sources |
| OpenShift clusters and OCP Advisor rules | OCP Advisor cluster and rule tools |
| Blueprints and composes | Image Builder list, detail, and compose tools |
| Roles and permissions | RBAC access and role tools |

For example, each CVE record's `affected_host_ids` must identify hosts returned by
Inventory, and an Advisor rule's `affected_host_ids` and `cve_ids` must point
to the corresponding catalog records. `catalog/context.py` derives values
such as `{host_id}`, `{hostname}`, `{cve_id}`, and `{rule_id}` from these same
relationships, so prompts and tool responses stay consistent.

The catalog integrity checks are kept separate from LLM execution:

```bash
env -u PHOENIX_COLLECTOR_ENDPOINT \
  uv run pytest -p no:rerunfailures -q \
  tests/mock_insights_api/catalog/test_validation.py
```

Run this after changing catalog entities or their relationships. The
validation checks IDs, required system profiles, foreign-key-like references,
and reciprocal CVE/Advisor relationships.

## Mocked service projections

`routes/__init__.py` registers the current route modules through
`register_all_routes()`:

| Toolset | API projection | Main mocked data |
| --- | --- | --- |
| Inventory | `api/inventory/v1` | Hosts, groups, tags, system profiles, repositories, and host relationships |
| Vulnerability | `api/vulnerability/v1` and `api/vmaas/v3` | Systems, CVE records, affected systems, system CVEs, and vulnerability queries |
| Advisor | `api/insights/v1` | Rules, rule statistics, affected systems, system details, and knowledge-base content |
| Remediations | `api/remediations/v1` | Resolution suggestions and dynamically registered remediation playbooks |
| Planning | `api/roadmap/v1` | Upcoming changes, RHEL lifecycle, and application streams |
| Image Builder | `api/image-builder/v1` | Distributions, blueprints, composes, and blueprint write operations |
| Content Sources | `api/content-sources/v1.0` | Repository lists and repository details |
| RHSM | `api/rhsm/v2` | Activation keys |
| OCP Advisor | `api/insights-results-aggregator/v2` | Cluster information, rules, rule content, and upgrade-risk predictions |
| RBAC | `api/rbac/v1` | Access records and roles |

These are projections, not duplicate client models. A route should return the
shape consumed by the tool, while the catalog should retain the shared entity
relationships needed by several routes.

### OpenAPI-backed routes

The Image Builder and Vulnerability projections expose the OpenAPI documents
used by their tools. Keep those documents aligned with the routes the mock
actually registers, especially when a tool asks for a reduced document such
as `POST:/blueprints` or `GET:/vulnerabilities/cves`.

The LLM-test fixture fetches the current full service documents once before it
starts the local mock server. All requests made by the MCP process then use
the fetched local documents; the mock never contacts the service during a
test. The fetched documents describe the complete service APIs; the mock still
registers only the endpoints currently used by the LLM scenarios.

The authoritative contract is the real tool implementation and the service
OpenAPI response. The mock data is synthetic; field names, request bodies,
response envelopes, status codes, and list/detail relationships should match
the real API closely enough for the tool and its LLM instructions to behave
the same way.

### Write and state-aware routes

Most current routes are read projections. The routes that accept bodies are
not all persistent writes:

- Remediation creation returns a deterministic ID and registers the matching
  playbook route so a later playbook request works.
- Image Builder create, update, and compose operations use mutable state owned
  by that mock API registration. New blueprints appear in list and detail
  responses, updates change the returned version and fields, and new composes
  appear in compose lists and can be fetched by ID.
- OCP Advisor upgrade-risk prediction and the vmaas vulnerability request are
  POST queries. They derive a response from the request and catalog; they do
  not create persistent entities.

Do not add a generic catch-all write response. If a write tool needs a new
state transition, model that transition explicitly in its route module and
register any follow-up endpoint the tool calls.

## Adding or extending mock data

When adding a tool or a new scenario:

1. Inspect the tool implementation to record the exact HTTP method, path,
   query parameters, request body, response shape, and follow-up calls.
2. Verify those details against the service OpenAPI document or the real API
   response. Do not infer a response shape only from a prompt description.
3. Reuse an existing catalog entity when the new response refers to an
   existing host, CVE record, rule, repository, cluster, blueprint, or compose.
4. Add a typed catalog field or entity only when the data is genuinely new.
   Put shared synthetic records in `catalog/data.py`; keep service-specific
   constants in `catalog/service_data.py` when they have no cross-service
   relationship.
5. Add the smallest response projection to the relevant file in `routes/`.
   Use the shared request, query, and pagination helpers where the behavior is
   common. Keep response envelopes and service-specific filtering local to
   the route module.
6. Register the exact endpoint in that route module. New route modules must
   also be added to `routes/__init__.py` so `register_all_routes()` includes
   them.
7. Extend `catalog/context.py` only when a prompt needs a new placeholder.
   The value should be selected from the catalog, not placed separately in
   the prompt fixture.
8. Run catalog validation, the relevant existing tests, and the repository
   lint hooks before committing.

Route registration is exact. Dynamic IDs therefore need explicit detail
routes. A state-aware route may register a new exact route after creating an
entity, as the Image Builder and Remediations projections do.

## Useful checks

```bash
# Catalog relationships.
uv run pytest -p no:rerunfailures -q tests/mock_insights_api/catalog/test_validation.py

# All LLM tests against the local catalog.
make test-llm

# Live Insights API validation for scheduled pipelines.
INSIGHTS_LLM_API_MODE=live make test-llm

# Inspect skipped scenarios and their missing live data.
env DEEPEVAL_TELEMETRY_OPT_OUT=YES uv run pytest -m llm -v -rs
```

For the scenario model, placeholder handling, model configuration, and LLM
fixture contract, see the
[`mcp_llm_eval` README](../mcp_llm_eval/README.md).
