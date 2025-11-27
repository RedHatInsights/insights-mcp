# Planning MCP Test Prompts

This file contains test prompts to validate the Planning MCP toolset integration with LLMs.

## Tool: get_upcoming_changes

### Test 1: List all upcoming changes
**Prompt:** "Show me all upcoming package changes in the roadmap."

**Expected Behavior:**
- Should call `planning__get_upcoming_changes` with no parameters.
- Should return the full list of upcoming package changes grouped by RHEL versions.

### Test 2: Filter by RHEL version (client-side)
**Prompt:** "What upcoming changes are planned for RHEL 9.4?"

**Expected Behavior:**
- Should call `planning__get_upcoming_changes` with no parameters.
- The model should then filter results for RHEL 9.4 and summarize the relevant entries in natural language.

### Test 3: Deprecations only (reasoning + summarization)
**Prompt:** "Which packages are going to be deprecated next year?"

**Expected Behavior:**
- Should call `planning__get_upcoming_changes` with no parameters.
- The model should identify entries that correspond to deprecations and summarize them, explaining timelines and impact.

### Test 4: Explain roadmap impact
**Prompt:** "Help me understand the main roadmap changes that might affect our RHEL 8 and 9 systems."

**Expected Behavior:**
- Should call `planning__get_upcoming_changes` with no parameters.
- The model should group and summarize changes relevant to RHEL 8 and RHEL 9, focusing on timelines and potential impact, and may provide light planning context if helpful.
