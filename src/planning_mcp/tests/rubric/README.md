# Rubric-Based LLM Evaluation Tests

This folder contains rubric-based tests for evaluating LLM behavior when interacting with the Planning MCP toolset. Tests use [rubric-kit](https://github.com/rubric-kit/rubric-kit) to define evaluation criteria and execute multi-judge consensus evaluation.

## Overview

The rubric testing framework provides a structured way to:

- **Define evaluation criteria** in YAML rubric files
- **Execute LLM prompts** against MCP servers with real tool execution
- **Evaluate responses** using a panel of LLM judges
- **Generate reports** (PDF/YAML) with detailed scoring breakdowns

## Important files from the folder structure

```
rubric/
├── README.md                           # This file
├── constants.py                        # Shared constants (paths, thresholds, LLM configs)
├── panel.yaml                          # Judge panel configuration
├── test_rubric_base.py                 # Base class and factory function
└── reports/                            # Generated evaluation reports (PDF/YAML)
```

## How to Add a New Test Case

### Option 1: Using the Factory Function (Recommended for Simple Tests)

Create a new test file or add to an existing one:

```python
# test_my_feature.py
from .test_rubric_base import create_rubric_test_class
from .constants import TEST_DIR

TestMyFeature = create_rubric_test_class(
    test_prompt="What is the status of package XYZ in RHEL 10?",
    report_title="Planning MCP - Package Status Query",
    expected_tool="planning__get_upcoming_changes",
    rubric_path=TEST_DIR / "test_my_feature_rubric.yaml"
)
```

### Option 2: Class inherit (For Complex Tests)

```python
# test_my_complex_feature.py
import pytest
from .test_rubric_base import BaseRubricTest
from .constants import TEST_DIR, LLM_CONFIGURATIONS
from tests.utils import should_skip_llm_matrix_tests

@pytest.mark.skipif(should_skip_llm_matrix_tests(), reason="No LLM configurations available")
@pytest.mark.parametrize("llm_config", LLM_CONFIGURATIONS, ids=lambda c: c.get("name", "Unknown Model"))
class TestMyComplexFeature(BaseRubricTest):
    TEST_PROMPT = "Your complex test prompt here"
    REPORT_TITLE = "My Complex Feature Test"
    EXPECTED_TOOL = "planning__get_upcoming_changes"
    RUBRIC_PATH = TEST_DIR / "test_my_complex_feature_rubric.yaml"
    PASSING_THRESHOLD = 85.0  # Override default threshold
```

---

## Configuration

### Constants (`constants.py`)

```python
TEST_DIR = Path(__file__).parent          # This rubric folder
PANEL_PATH = TEST_DIR / "panel.yaml"      # Judge panel config
PASSING_THRESHOLD = 80.0                  # Default minimum score
LLM_CONFIGURATIONS = load_llm_configurations()  # From test_config.json
```

### Environment Variables

| Variable                      | Description                                                                                   |
|-------------------------------|-----------------------------------------------------------------------------------------------|
| `GEMINI_API_KEY`              | API key for Gemini judge models. [Optional] Needed if using Gemini in `judges.yaml`, see [LLM Provider Setup](https://github.com/narmaku/rubric-kit?tab=readme-ov-file#llm-provider-setup)          |
| `GENERATE_REPORTS`            | Set to `true` to generate PDF/YAML reports after test execution.                             |
| `DEEPEVAL_TELEMETRY_OPT_OUT`  | Set to `YES` to disable telemetry.                                                           |
| `INSIGHTS_CLIENT_ID`          | Your Insights user client ID.                                                                |
| `INSIGHTS_CLIENT_SECRET`      | Your Insights user API secret token.                                                         |
| `SSL_CERT_FILE`               | Default path to local certificate for SSL connections (e.g., `/etc/ssl/cert.pem`).           |

---

## Reports

When `GENERATE_REPORTS=true`, reports are saved to `reports/`:

- **YAML**: Machine-readable evaluation data
- **PDF**: Human-readable formatted report

Report filenames: `evaluation_{model_name}_{timestamp}.{yaml|pdf}`

---

## Tips for Writing Good Tests

1. **Be specific in test prompts** — Vague prompts lead to variable behavior
2. **Match rubric to prompt** — Criteria should evaluate what the prompt asks for
3. **Use appropriate weights** — Critical criteria (like tool correctness) should have higher weights
4. **Write clear criterion text** — Judges use this to evaluate; be explicit about expectations
5. **Start with existing examples** — Copy and modify `test_upcoming`
