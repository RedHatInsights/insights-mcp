# Lean Business Case: Red Hat Lightspeed MCP Server

## Problem Statement

Red Hat customers managing RHEL infrastructure must navigate multiple console.redhat.com services — Advisor, Inventory, Vulnerability, Image Builder, Planning, and Remediations — each with its own UI and API. Operators context-switch between dashboards and manually correlate data across services. Meanwhile, LLM-based assistants are becoming the primary operator interface but have no native access to Red Hat Lightspeed services.

## Goals

1. **Unified natural-language access** to Red Hat Lightspeed services via a single MCP server, usable from any MCP-compatible client.
2. **Reduce time-to-insight** by letting LLM agents orchestrate multi-service queries in one conversational turn.
3. **Security-first design** with read-only defaults, RBAC-scoped service accounts, and emergency credential revocation.
4. **Broad client compatibility** across STDIO, SSE, and HTTP streaming transports.

## Expected Outcomes

| Outcome | Measure |
|---------|---------|
| Faster infrastructure triage | Multi-service questions answered in one turn instead of 3-4 separate UIs |
| Lower barrier to API adoption | Natural language replaces learning individual API contracts |
| Improved security visibility | CVE exposure, advisor recommendations, and lifecycle risks surfaced proactively |
| Increased remediation velocity | Vulnerability discovery to Ansible playbook creation in one session |
| Broader ecosystem reach | Works across VS Code, Cursor, Claude Desktop, Gemini CLI, and CLine |

## Target Users

- **Platform engineers / SREs** managing RHEL fleets registered with Red Hat Insights
- **Security teams** triaging CVEs and tracking remediation
- **IT operations** planning RHEL lifecycle upgrades and application stream migrations
- **Developers** building custom RHEL images via Image Builder

## Key Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Over-permissioned AI actions | Read-only default; write tools require `--all-tools`; RBAC enforces permissions |
| Credential exposure | Credentials via env vars or headers, never persisted; documented kill-switch for revocation |
| Transport security (remote) | Documentation warns against internet exposure; JWT and OAuth/DCR flows for hosted scenarios |

## Success Criteria

- All supported Lightspeed service toolsets accessible and functional via MCP protocol.
- Automated integration tests passing for each toolset.
- At least 5 MCP client integrations documented and verified.
- Read-only default enforced; no write operation possible without explicit opt-in.
