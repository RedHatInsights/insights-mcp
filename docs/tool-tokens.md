# MCP tool input tokens

Encoding: `cl100k_base`

Counts cover the OpenAI-style `tools` payload only (names, descriptions, schemas).
Every row uses `--all-tools` (maximum tools per mode).

| Mode | Tools | Input tokens |
|------|------:|-------------:|
| all-tools | 55 | 13076 |
| advisor | 12 | 1816 |
| content-sources | 7 | 1244 |
| image-builder | 15 | 1677 |
| inventory | 14 | 3014 |
| ocp-advisor | 10 | 1791 |
| planning | 11 | 4131 |
| rbac | 5 | 707 |
| remediations | 6 | 905 |
| rhsm | 7 | 1048 |
| vulnerability | 13 | 3106 |
