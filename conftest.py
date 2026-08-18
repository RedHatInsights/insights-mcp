"""Root conftest — overrides mcp_llm_eval defaults for this project."""

import nest_asyncio

# Prevent Python 3.14 event loop corruption caused by deepeval calling
# nest_asyncio.apply().
nest_asyncio.apply = lambda: None
