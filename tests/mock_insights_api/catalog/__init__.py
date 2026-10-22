"""Canonical data and models for the test-only Insights API mock."""

from tests.mock_insights_api.catalog.context import build_llm_api_context
from tests.mock_insights_api.catalog.data import DEFAULT_CATALOG, FIXTURE_NOW
from tests.mock_insights_api.catalog.errors import CatalogValidationError
from tests.mock_insights_api.catalog.models import (
    CVE,
    AdvisorRule,
    ApplicationStreamRecord,
    CatalogIndexes,
    Host,
    MockCatalog,
    RepositoryReference,
    RHELLifecycleRecord,
    SystemProfile,
    Tag,
    UpcomingChange,
    Workspace,
)
from tests.mock_insights_api.catalog.validation import validate_catalog

__all__ = [
    "CVE",
    "ApplicationStreamRecord",
    "CatalogIndexes",
    "CatalogValidationError",
    "DEFAULT_CATALOG",
    "FIXTURE_NOW",
    "AdvisorRule",
    "Host",
    "MockCatalog",
    "RepositoryReference",
    "RHELLifecycleRecord",
    "SystemProfile",
    "Tag",
    "UpcomingChange",
    "Workspace",
    "build_llm_api_context",
    "validate_catalog",
]
