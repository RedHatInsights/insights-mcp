"""Utilities for running async code from synchronous contexts."""

import asyncio
import concurrent.futures


def run_async(coro):
    """Run a coroutine from sync code, including when an event loop is already running."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()
