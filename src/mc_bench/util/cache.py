"""
Caching utility functions for MC-Bench.
"""

from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict

from .logging import get_logger

logger = get_logger(__name__)

# Process-level cache with expiry time
_cache: Dict[str, Dict[str, Any]] = {}


def timed_cache(hours: int = 12):
    """
    Function decorator that caches the result with a specified expiry time.

    Args:
        hours: Number of hours to keep the cache valid

    Returns:
        Decorator function that wraps the original function
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key based on the function name
            cache_key = func.__name__

            # Check if we have a valid cache entry
            if cache_key in _cache:
                entry = _cache[cache_key]
                if datetime.now() < entry["expiry"]:
                    return entry["data"]

            # No valid cache, call the function
            data = func(*args, **kwargs)

            # Store the result with expiry time
            _cache[cache_key] = {
                "data": data,
                "expiry": datetime.now() + timedelta(hours=hours),
            }

            logger.info(f"Cached {cache_key} for {hours} hours")
            return data

        return wrapper

    return decorator
