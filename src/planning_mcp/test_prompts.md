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
## Tool: get_relevant_upcoming_changes

### Test 1: List all relevant upcoming changes
**Prompt:** "Show me all relevant upcoming changes for my systems."

**Expected Behavior:**
- Should call `planning__get_relevant_upcoming_changes` with no parameters (major and minor are optional).
- Should return the full list of upcoming package changes relevant to all systems in the user's inventory.
- Model should summarize the changes and highlight potentially affected systems.

### Test 2: Filter by RHEL major version
**Prompt:** "What relevant upcoming changes affect my RHEL 9 systems?"

**Expected Behavior:**
- Should call `planning__get_relevant_upcoming_changes` with `major=9`.
- Should return changes relevant to systems running RHEL 9.x.
- Model should summarize the changes and highlight potentially affected systems.

### Test 3: Filter by specific RHEL major.minor version
**Prompt:** "Show me relevant upcoming changes for my RHEL 9.2 systems"

**Expected Behavior:**
- Should call `planning__get_relevant_upcoming_changes` with `major=9` and `minor=2`.
- Should return changes relevant specifically to systems running RHEL 9.2.
- Model should explain the changes and list which of the user's RHEL 9.2 systems may be affected.

## Tool: get_relevant_appstreams

### Test 1: List all relevant appstreams
**Prompt:** "What application streams are relevant to my systems, including related successor streams?"

**Expected Behavior:**
- Should call `planning__get_relevant_appstreams` with default parameters (include_related=true).
- Should return all application streams in use across the user's inventory, including related/successor streams.
- Model should summarize the appstreams by application (e.g., Node.js, PostgreSQL) and highlight support status.

### Test 2: Only currently-used appstreams (no related streams)
**Prompt:** "Show me only the application streams that are actually installed on my systems, without any suggestions."

**Expected Behavior:**
- Should call `planning__get_relevant_appstreams` with `include_related=false`.
- Should return only the appstreams currently in use, without related or successor streams.
- Model should present a focused list of what's actually deployed.

### Test 3: Filter by RHEL major version
**Prompt:** "What application streams are relevant to my RHEL 9 systems and any related successor streams"

**Expected Behavior:**
- Should call `planning__get_relevant_appstreams` with `major=9` and `include_related=true` (default).
- Should return appstreams relevant to systems running RHEL 9.x, including related streams.
- Model should summarize the results and may highlight upgrade paths or newer versions.

### Test 4: Filter by specific RHEL major.minor version
**Prompt:** "Show me the appstreams relevant to my RHEL 9.2 systems and any related successor streams"

**Expected Behavior:**
- Should call `planning__get_relevant_appstreams` with `major=9`, `minor=2`, and `include_related=true` (default).
- Should return appstreams relevant specifically to systems running RHEL 9.2.
- Model should list the streams and may identify which systems are using them.

### Test 5: Identify upgrade opportunities
**Prompt:** "Are there newer versions of the application streams I'm using that I should consider upgrading to?"

**Expected Behavior:**
- Should call `planning__get_relevant_appstreams` with `include_related=true` (default).
- Model should analyze the results, identify where related streams with newer versions exist.
- Should provide recommendations for potential upgrades with support timeline context.

### Test 6: Check support status for specific appstream
**Prompt:** "Is the Node.js version in our inventory still supported, and are there newer options available?"

**Expected Behavior:**
- Should call `planning__get_relevant_appstreams` with `include_related=true` (default).
- Model should filter results for Node.js streams, explain support status and end dates.
- Should highlight related/newer Node.js versions if available and provide migration guidance.

## Tool: get_relevant_rhel_lifecycle

### Test 1: List all relevant RHEL lifecycle information
**Prompt:** "What RHEL versions are currently running in my environment and when do they go out of support?"

**Expected Behavior:**
- Should call `planning__get_relevant_rhel_lifecycle` with no parameters (defaults: `include_related=false`).
- Should return RHEL lifecycle information for all versions observed in the user's inventory.
- Model should summarize support status and end dates for each version found.

### Test 2: Filter by RHEL major version
**Prompt:** "Show me the lifecycle status of my RHEL 8 systems."

**Expected Behavior:**
- Should call `planning__get_relevant_rhel_lifecycle` with `major=8`.
- Should return lifecycle information only for RHEL 8.x systems in the user's inventory.
- Model should summarize support timelines and highlight any versions nearing end-of-support.

### Test 3: Filter by specific RHEL major.minor version
**Prompt:** "Show me the lifecycle status of my RHEL 9.2 systems?"

**Expected Behavior:**
- Should call `planning__get_relevant_rhel_lifecycle` with `major=9` and `minor=2`.
- Should return lifecycle information specifically for RHEL 9.2 systems in the user's inventory.
- Model should explain support status, end dates and any recommended actions.

### Test 4: Include related versions for upgrade planning
**Prompt:** "What RHEL 9 minor versions could I upgrade my systems to that are still supported?"

**Expected Behavior:**
- Should call `planning__get_relevant_rhel_lifecycle` with `major=9` and `include_related=true`.
- Should return both currently deployed RHEL 8 versions and related higher-minor versions that are still supported but not yet deployed (marked as `related=true`).
- Model should identify upgrade targets by highlighting versions with `related=true` and compare their support timelines to currently running versions.
