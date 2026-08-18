---
name: getting-started
description: >
  Help users set up and start using the Red Hat Lightspeed MCP server for
  managing RHEL systems via AI agents. Use when the user asks how to install,
  configure, or connect the MCP server, needs help with authentication
  (service accounts, credentials, tokens), wants to know what toolsets are
  available, asks what they can do with this project, or is looking for
  first-steps guidance — even if they just say "get started", "how do I use
  this", or "what can I do".
license: Apache-2.0
metadata:
  author: RedHatInsights
  version: "1.0"
---

# Getting Started with Red Hat Lightspeed MCP

Guide the user from zero to a working MCP connection. Adapt the steps below
to their situation — ask which MCP client they use and whether they already
have a Red Hat service account before walking through everything.

## Install Skills with Lola (optional)

If the user wants the Lightspeed MCP skills installed into their AI assistant
without cloning the full repo, they can use
[Lola](https://docs.getlola.dev/) — a universal AI Context Package Manager.

```bash
# Install Lola (one-time)
uv tool install git+https://github.com/RedHatProductSecurity/lola

# Add the Lightspeed marketplace (one-time)
lola market add lightspeed https://raw.githubusercontent.com/RedHatInsights/insights-mcp/main/lola-marketplace.yml

# Install skills to your AI assistant
lola install rh-lightspeed-mcp-skills -a cursor
lola install rh-lightspeed-mcp-skills -a claude-code
lola install rh-lightspeed-mcp-skills -a gemini-cli
```

This installs the skills to the assistant's native directory (e.g.,
`.cursor/skills/`, `.claude/skills/`). Users who clone the repo already have
the skills in `.agents/skills/` — Lola is for distribution without cloning.

## Setup Flow

### 1. Prerequisites

The user needs:
- `podman` or `docker` installed
- A Red Hat account at https://console.redhat.com
- An MCP-compatible client

On macOS, if `podman` is installed but the client can't find it, use the full
path from `which podman` (usually `/opt/homebrew/bin/podman` or
`/usr/local/bin/podman`).

### 2. Authentication

**THIS STEP MUST BE PERFORMED BY THE USER — NOT BY THE AGENT.**
Do not attempt to create, modify, or manage service accounts or permissions
on behalf of the user. Only provide instructions and let the user act.

The user needs a Red Hat service account. Direct them to do the following:

1. Go to https://console.redhat.com → Settings (gear icon) → "Service Accounts"
2. Create a service account → save the **Client ID** and **Client Secret**
3. Provide those values as `LIGHTSPEED_CLIENT_ID` and `LIGHTSPEED_CLIENT_SECRET`

Service accounts have **no permissions by default**. An org admin must grant
roles via Settings → User Access → Groups. Tell the user which roles are
needed based on the toolsets they plan to use:

| Toolset | Required Roles |
|---|---|
| advisor | RHEL Advisor viewer |
| inventory | Inventory Hosts viewer |
| vulnerability | Vulnerability viewer, Inventory Hosts viewer |
| remediations | Remediations user |

If API calls return **403**, this is almost always a missing role — tell the
user to check their service account permissions.

For a step-by-step video walkthrough of granting permissions, direct the user
to: https://www.youtube.com/watch?v=UvNcmJsbg1w

### 3. Connect the MCP Client

Ask the user which client they're using.

Detailed per-client configuration (Cursor, VS Code, Claude Desktop, Claude
Code, Goose, Gemini CLI, CLine, HTTP transport, generic STDIO) is in the
project README. When this skill is installed via Lola, the README is available
at `../README.md` relative to this file. If the user cloned the repo, it's at
the project root.

Look up the matching section in the README and walk the user through it.

### 4. Choose Toolsets

All toolsets load by default. To limit which ones are active, add
`--toolset=<name>,<name>` to the container args.

| Toolset | What it does |
|---|---|
| **vulnerability** | CVE analysis, system-CVE mapping, explain why CVEs affect your systems |
| **advisor** | Configuration issue recommendations (availability, stability, performance, security) |
| **inventory** | Host discovery, system profiles, tags, fleet overview |
| **image-builder** | Create and manage custom RHEL image blueprints and composes |
| **remediations** | Generate Ansible playbooks to fix CVEs on specific systems |
| **planning** | RHEL and AppStream lifecycle dates, upcoming deprecations and changes |
| **rhsm** | Activation keys for Red Hat Subscription Management |
| **content-sources** | Repository listing and filtering |
| **rbac** | Query your role-based access permissions |

### 5. Verify the Connection

Suggest these prompts to confirm things work end-to-end:

- "List my top 5 most recently active hosts" (tests inventory + auth)
- "Show me the top 5 critical CVEs affecting my account" (tests vulnerability)
- "What advisor recommendations are impacting my systems?" (tests advisor)

If any fail with an auth error, call `get_mcp_version` to check whether the
server is up-to-date, and revisit the permissions table above.

## Gotchas

- **Read-only by default.** Write tools (create blueprints, compose images,
  create remediation playbooks) are hidden unless the server is started with
  `--all-tools`. If the user asks to create something and the tool doesn't
  exist, tell them to add `--all-tools` to the container args and restart.
- **Tool naming convention.** Every tool is prefixed with its toolset name:
  `vulnerability_get_cves`, `advisor_get_active_rules`, `inventory_list_hosts`.
  Always use the full prefixed name.
- **Cursor tool name length limit.** If Cursor says "Some tools have naming
  issues and may be filtered out", the server name in `mcp.json` is too long.
  Use `lightspeed-mcp` (not `red-hat-lightspeed-mcp`).
- **macOS podman path.** Some clients can't find `podman` on macOS. Replace
  `podman` with the full path from `which podman` (usually
  `/opt/homebrew/bin/podman` or `/usr/local/bin/podman`).
- **Cached tool descriptions.** After rebuilding the container, fully restart
  the IDE — the "restart MCP server" button doesn't always pick up new tool
  descriptions.
- **Version checking.** If something seems broken, call `get_mcp_version`. It
  compares the running version against the latest GitHub release and shows
  what changed between them.
- **Podman on macOS with HTTP/SSE.** When using podman machine on macOS, set
  the host explicitly and expose the port:
  `podman run -p 8000:8000 --rm ghcr.io/redhatinsights/red-hat-lightspeed-mcp:latest http --host 0.0.0.0`

## Security

- Never expose the container to the internet when running locally.
- Credentials are transferred to the MCP server — only trust servers you
  control.
- To revoke access immediately: stop the container, then delete or reset the
  service account at https://console.redhat.com/iam/service-accounts.
