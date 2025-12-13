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

## Tool: get_appstreams_lifecycle

### Test 1: List all upcoming changes
**Prompt:** "What versions of Node.js are available across RHEL 8, 9, and 10?"

**Expected Behavior:**
- Should call `planning__get_appstreams_lifecycle` with:
  ```json
  { "mode": "streams", "application_stream_name": "Node.js" }
  ```
- Should return a list of Node.js application streams across supported RHEL versions.

### Test 2: Detailed Lifecycle (raw mode, major scope)
**Prompt:** "Show me the detailed lifecycle of all modules available on RHEL 9."

**Expected Behavior:**
- Should call `planning__get_appstreams_lifecycle` with:
  ```json
  { "mode": "raw", "major": 9 }
  ```
- Should return the full raw lifecycle dataset for RHEL 9.
- The output may be grouped or formatted, but raw lifecycle rows must remain available.


### Test 3: Specific Package / Major Validation
**Prompt:** "Is the 'postgresql' package supported on RHEL 8, and when does it expire?"

**Expected Behavior:**
- Should call `planning__get_appstreams_lifecycle` with:
  ```json
  { "mode": "raw", "major": 8, "name": "postgresql" }
  ```
- Should extract lifecycle status and end-of-life date from the results.

## Tool: get_rhel_lifecycle

### Test 1: List all RHEL lifecycle information
**Prompt:** "Give me complete list of the available RHEL versions and their support status."

**Expected Behavior**
- Should call `planning__get_rhel_lifecycle` with no parameters
- Should return information about all RHEL major and minor versions provided by RHEL Life cycle API; from RHEL 7 until, at least, RHEL 11.

### Test 2: Filter specific RHEL version
**Prompt:** "What is the support status of RHEL 10.1?"

**Expected Behavior:**
- Should call `planning__get_rhel_lifecycle` with no parameters
- The model should filter life cycle information for RHEL 10.1 and provide information about the support status.

### Test 3: Retirements only
**Prompt:** "Which RHEL version are going to be retired next year?"

**Expected Behavior:**
- Should call `planning__get_rhel_lifecycle` with no parameters
- Should summarize which RHEL versions are going to be retired next year and provide recommendations about upgrades.

### Test 4: Question about specific RHEL version after support
**Prompt:** "I'm using RHEL 8.8. Are there any actions regarding my RHEL version I should take?"

**Expected Behavior**
- Should call `planning__get_rhel_lifecycle` with no parameters
- Should recommend upgrade to newer RHEL minor version, switch support plan and upgrade to newer major version.
