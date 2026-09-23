# MCP tool input tokens

Encoding: `cl100k_base`

Counts cover the OpenAI-style `tools` payload only (names, descriptions, schemas).
Every row uses `--all-tools` (maximum tools per mode).

| Mode | Tools | Input tokens |
|------|------:|-------------:|
| all-tools | 46 | 12588 |
| advisor | 8 | 2224 |
| content-sources | 2 | 489 |
| image-builder | 11 | 1053 |
| inventory | 10 | 2392 |
| planning | 7 | 3507 |
| rbac | 2 | 249 |
| remediations | 2 | 432 |
| rhsm | 3 | 424 |
| vulnerability | 9 | 2482 |
