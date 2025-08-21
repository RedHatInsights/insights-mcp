```
usage: insights-mcp [-h] [--debug] [--stage] [--toolset TOOLSET]
                    [--toolset-help]
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
  --stage            Use stage API instead of production API
  --toolset TOOLSET  Comma-separated list of toolsets to use. Available
                     toolsets: all, image-builder, vulnerability,
                     remediations, advisor, inventory (default: all)
  --toolset-help     Show toolset details of all toolsets
```
