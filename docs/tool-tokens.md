# MCP tool input tokens

Encoding: `cl100k_base`

Counts cover the OpenAI-style `tools` payload only (names, descriptions, schemas).
Every row uses `--all-tools` (maximum tools per mode).

| Mode | Tools | Input tokens |
|------|------:|-------------:|
| all-tools | 49 | 13023 |
| advisor | 12 | 2827 |
| content-sources | 6 | 1092 |
| image-builder | 15 | 1656 |
| inventory | 14 | 2993 |
| planning | 11 | 4110 |
| rbac | 5 | 686 |
| remediations | 6 | 1035 |
| rhsm | 7 | 1027 |
| vulnerability | 13 | 3085 |
