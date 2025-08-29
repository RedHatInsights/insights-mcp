# Content Sources MCP Test Prompts

This file contains test prompts to validate the Content Sources MCP toolset integration with LLMs.

## Basic Functionality Tests

### Test 1: List All Repositories
**Prompt:** "List all repositories from content sources"

**Expected Behavior:**
- Should call `content-sources_list_repositories` with default parameters
- Should return a list of repositories with pagination info

### Test 2: List Repositories with Filtering
**Prompt:** "Show me repositories that are enabled and have content type 'rpm'"

**Expected Behavior:**
- Should call `content-sources_list_repositories` with `enabled=True` and `content_type="rpm"`
- Should return filtered list of RPM repositories that are enabled

### Test 3: Search by Name
**Prompt:** "Find repositories with 'rhel' in the name"

**Expected Behavior:**
- Should call `content-sources_list_repositories` with `name="rhel"`
- Should return repositories containing "rhel" in their name

### Test 4: Pagination Test
**Prompt:** "Show me the first 5 repositories"

**Expected Behavior:**
- Should call `content-sources_list_repositories` with `limit=5`
- Should return exactly 5 repositories (or fewer if total < 5)

### Test 5: Architecture Filter
**Prompt:** "List repositories for x86_64 architecture"

**Expected Behavior:**
- Should call `content-sources_list_repositories` with `arch="x86_64"`
- Should return repositories specific to x86_64 architecture

### Test 6: Version Filter
**Prompt:** "Show repositories for RHEL 9"

**Expected Behavior:**
- Should call `content-sources_list_repositories` with `version="9"`
- Should return repositories for RHEL 9

### Test 7: Origin Filter
**Prompt:** "List only Red Hat repositories"

**Expected Behavior:**
- Should call `content-sources_list_repositories` with `origin="red_hat"`
- Should return only repositories from Red Hat origin

### Test 8: URL Search
**Prompt:** "Find repositories with 'baseos' in the URL"

**Expected Behavior:**
- Should call `content-sources_list_repositories` with `url="baseos"`
- Should return repositories containing "baseos" in their URL

### Test 9: Combined Filters
**Prompt:** "Show enabled RPM repositories for x86_64 architecture with 'appstream' in the name"

**Expected Behavior:**
- Should call `content-sources_list_repositories` with multiple filters:
  - `enabled=True`
  - `content_type="rpm"`
  - `arch="x86_64"`
  - `name="appstream"`
- Should return repositories matching all criteria

### Test 10: Disabled Repositories
**Prompt:** "List all disabled repositories"

**Expected Behavior:**
- Should call `content-sources_list_repositories` with `enabled=False`
- Should return only disabled repositories

## Error Handling Tests

### Test 11: Invalid Parameters
**Prompt:** "List repositories with limit 1000"

**Expected Behavior:**
- Should call `content-sources_list_repositories` with `limit=1000`
- Should handle large limit gracefully (API may have its own limits)

### Test 12: No Results
**Prompt:** "Find repositories with name 'nonexistent-repo'"

**Expected Behavior:**
- Should call `content-sources_list_repositories` with `name="nonexistent-repo"`
- Should return empty results gracefully

## Complex Queries

### Test 13: Repository Analysis
**Prompt:** "Analyze my repository setup - show me all repositories grouped by content type"

**Expected Behavior:**
- Should call `content-sources_list_repositories` to get all repositories
- Should process and group results by content_type
- Should provide analysis of repository distribution

### Test 14: Repository Health Check
**Prompt:** "Check the health of my repositories - show me disabled repositories and any with errors"

**Expected Behavior:**
- Should call `content-sources_list_repositories` with `enabled=False`
- Should analyze repository status and identify potential issues
- Should provide recommendations for repository health

### Test 15: Repository Inventory
**Prompt:** "Give me a complete inventory of all my content sources repositories"

**Expected Behavior:**
- Should call `content-sources_list_repositories` to get comprehensive list
- Should provide organized summary of all repositories
- Should include counts by type, origin, architecture, etc.
