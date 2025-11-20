```
usage: insights-mcp [-h] [--debug] [--toolset TOOLSET] [--toolset-help]
                    [--readonly]
                    {stdio,sse,http} ...

Run Insights MCP server.

positional arguments:
  {stdio,sse,http}   Transport mode
    stdio            Use stdio transport (default)
    sse              Use SSE transport
    http             Use HTTP streaming transport

options:
  -h, --help         show this help message and exit
  --debug            Enable debug logging
  --toolset TOOLSET  Comma-separated list of toolsets to use. Available
                     toolsets: all, image-builder, rhsm, vulnerability,
                     remediations, advisor, inventory, content-sources, rbac,
                     planning (default: all)
  --toolset-help     Show toolset details of all toolsets
  --readonly         Only register read-only tools
```
