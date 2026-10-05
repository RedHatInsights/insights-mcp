# MCP tool input tokens

Encoding: `cl100k_base`

Counts cover the OpenAI-style `tools` payload only (names, descriptions, schemas).
Every row uses `--all-tools` (maximum tools per mode).

| Mode | Tools | Input tokens |
|------|------:|-------------:|
| all-tools | 51 | 13047 |
| advisor | 12 | 2845 |
| content-sources | 6 | 1110 |
| image-builder | 15 | 1674 |
| inventory | 14 | 3011 |
| ocp-advisor | 7 | 861 |
| planning | 11 | 4128 |
| rbac | 5 | 704 |
| remediations | 6 | 902 |
| rhsm | 7 | 1045 |
| vulnerability | 13 | 3103 |
