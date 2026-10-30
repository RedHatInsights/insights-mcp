# MCP tool input tokens

Encoding: `cl100k_base`

Counts cover the OpenAI-style `tools` payload only (names, descriptions, schemas).
Every row uses `--all-tools` (maximum tools per mode).

| Mode | Tools | Input tokens |
|------|------:|-------------:|
| all-tools | 56 | 12839 |
| advisor | 12 | 1803 |
| content-sources | 7 | 1229 |
| image-builder | 15 | 1669 |
| inventory | 14 | 3006 |
| ocp-advisor | 11 | 1642 |
| planning | 11 | 4047 |
| rbac | 5 | 699 |
| remediations | 6 | 897 |
| rhsm | 7 | 1040 |
| vulnerability | 13 | 3098 |
