"""Catalog-backed route registrars for the LLM-test API mock."""

from tests.mock_insights_api.routes.inventory import register_inventory_routes
from tests.mock_insights_api.routes.vulnerability import register_vulnerability_routes

__all__ = ["register_inventory_routes", "register_vulnerability_routes"]
