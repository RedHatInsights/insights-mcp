# MCP tool input tokens

Encoding: `cl100k_base`

Counts cover the OpenAI-style `tools` payload only (names, descriptions, schemas).
Every row uses `--all-tools` (maximum tools per mode).

| Mode | Tools | Input tokens |
|------|------:|-------------:|
| all-tools | 41 | 10663 |
| advisor | 8 | 2222 |
| content-sources | 2 | 404 |
| image-builder | 11 | 1034 |
| inventory | 6 | 1043 |
| planning | 7 | 3507 |
| rbac | 2 | 247 |
| remediations | 2 | 430 |
| rhsm | 3 | 422 |
| vulnerability | 8 | 2002 |
