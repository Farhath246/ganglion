"""
Safety primitives - a rate limiter and a guarded-call decorator.

The rate limiter is the "don't thrash" constraint: a brain that acts
faster than the world can respond just gets more noise. `guarded`
turns a failure inside one step into a value instead of an exception,
so a single bad action step degrades the cycle rather than killing it.
"""

import functools
import time


def guarded(fallback=None):
    """Wrap a call so exceptions return `fallback` instead of raising."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception:
                return fallback
        return wrapper
    return deco


class RateLimiter:
    def __init__(self, max_calls: int = 30, per_seconds: float = 60):
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        self.calls = []

    def wait_if_needed(self):
        """Block until another call fits inside the window."""
        now = time.monotonic()
        self.calls = [t for t in self.calls if now - t < self.per_seconds]
        if len(self.calls) >= self.max_calls:
            sleep_for = self.per_seconds - (now - self.calls[0])
            if sleep_for > 0:
                time.sleep(sleep_for)
            now = time.monotonic()
            self.calls = [t for t in self.calls if now - t < self.per_seconds]
        self.calls.append(now)
