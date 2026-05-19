"""Cross-module retry decorator with exponential backoff."""
from __future__ import annotations

import asyncio
import functools
import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple = (Exception,),
):
    """Decorator for retrying async functions with exponential backoff.

    Usage::

        @with_retry(max_attempts=3, exceptions=(httpx.HTTPStatusError,))
        async def fetch_data(url: str) -> bytes:
            ...

    Args:
        max_attempts: Maximum number of attempts (including the first call).
        base_delay: Initial delay in seconds before the first retry.
        max_delay: Upper bound on the delay between retries.
        exceptions: Tuple of exception types that trigger a retry.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: BaseException | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt == max_attempts:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__name__,
                            max_attempts,
                            exc,
                        )
                        raise
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    logger.warning(
                        "%s attempt %d failed: %s, retrying in %.1fs",
                        func.__name__,
                        attempt,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator
