"""Integration tests for Rubric functionality with MCP server using rubric-kit."""

from .constants import TEST_DIR
from .test_rubric_base import create_rubric_test_class

TestUpcomingChangesRoadmap = create_rubric_test_class(
    test_prompt="Can you show me the full roadmap of upcoming package deprecations and additions for RHEL 10?",
    report_title="Planning MCP - Get Upcoming Changes General",
    expected_tool="planning__get_upcoming_changes",
    rubric_path=TEST_DIR / "test_upcoming_roadmap_rubric.yaml",
)

TestUpcomingChangesModelFiltering = create_rubric_test_class(
    test_prompt="List all package removals if I want to update from RHEL 9.2 to RHEL 10.",
    report_title="Planning MCP - Get Upcoming Changes Model Filtering",
    expected_tool="planning__get_upcoming_changes",
    rubric_path=TEST_DIR / "test_upcoming_model_filtering_rubric.yaml",
)
