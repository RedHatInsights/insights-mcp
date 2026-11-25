"""Canonical data and models for the test-only Insights API mock."""

from tests.mock_insights_api.catalog.context import build_llm_api_context
from tests.mock_insights_api.catalog.data import DEFAULT_CATALOG, FIXTURE_NOW
from tests.mock_insights_api.catalog.errors import CatalogValidationError
from tests.mock_insights_api.catalog.models import (
    CVE,
    ActivationKey,
    AdvisorRule,
    ApplicationStreamRecord,
    CatalogIndexes,
    ContentSourceRepository,
    Host,
    ImageBlueprint,
    ImageCompose,
    ImageDistribution,
    MockCatalog,
    OCPAdvisorCluster,
    OCPAdvisorRule,
    RBACRole,
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
    "ActivationKey",
    "ApplicationStreamRecord",
    "CatalogIndexes",
    "CatalogValidationError",
    "ContentSourceRepository",
    "DEFAULT_CATALOG",
    "FIXTURE_NOW",
    "AdvisorRule",
    "Host",
    "ImageBlueprint",
    "ImageCompose",
    "ImageDistribution",
    "MockCatalog",
    "OCPAdvisorCluster",
    "OCPAdvisorRule",
    "RBACRole",
    "RepositoryReference",
    "RHELLifecycleRecord",
    "SystemProfile",
    "Tag",
    "UpcomingChange",
    "Workspace",
    "build_llm_api_context",
    "validate_catalog",
]
