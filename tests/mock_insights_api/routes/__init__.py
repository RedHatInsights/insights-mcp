"""Catalog-backed route registrars for the LLM-test API mock."""

from tests.mock_insights_api.routes.advisor import register_advisor_routes
from tests.mock_insights_api.routes.image_builder import register_image_builder_routes
from tests.mock_insights_api.routes.inventory import register_inventory_routes
from tests.mock_insights_api.routes.planning import register_planning_routes
from tests.mock_insights_api.routes.remediations import register_remediations_routes
from tests.mock_insights_api.routes.vulnerability import register_vulnerability_routes

__all__ = [
    "register_advisor_routes",
    "register_image_builder_routes",
    "register_inventory_routes",
    "register_planning_routes",
    "register_remediations_routes",
    "register_vulnerability_routes",
]
