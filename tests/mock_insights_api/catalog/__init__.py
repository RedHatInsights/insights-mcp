"""Canonical data and models for the test-only Insights API mock."""

from tests.mock_insights_api.catalog.context import build_llm_api_context
from tests.mock_insights_api.catalog.data import DEFAULT_CATALOG, FIXTURE_NOW
from tests.mock_insights_api.catalog.errors import CatalogValidationError
from tests.mock_insights_api.catalog.models import (
    CVE,
    AdvisorRule,
    CatalogIndexes,
    Host,
    MockCatalog,
    RepositoryReference,
    SystemProfile,
    Tag,
    Workspace,
)
from tests.mock_insights_api.catalog.validation import validate_catalog

__all__ = [
    "CVE",
    "CatalogIndexes",
    "CatalogValidationError",
    "DEFAULT_CATALOG",
    "FIXTURE_NOW",
    "AdvisorRule",
    "Host",
    "MockCatalog",
    "RepositoryReference",
    "SystemProfile",
    "Tag",
    "Workspace",
    "build_llm_api_context",
    "validate_catalog",
]
