"""Constants for rubric-kit based LLM evaluation tests."""

from pathlib import Path

from tests.utils import load_llm_configurations

TEST_DIR = Path(__file__).parent
PANEL_PATH = TEST_DIR / "panel.yaml"
PASSING_THRESHOLD = 80.0
LLM_CONFIGURATIONS, _ = load_llm_configurations()
