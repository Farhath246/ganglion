"""
Homeostasis - the body's resource governor.

Brains don't run flat out; they throttle when the body is strained.
This reads two crude strain signals - CPU seconds burned since the last
check, and peak resident memory - and, when either crosses its
threshold, asks for a lower action rate. The thresholds are the point:
no threshold set means no throttling, so the default is "run normally".
"""

import resource
import time


class Homeostasis:
    def __init__(self, cpu_threshold: float = None, memory_threshold: float = None,
                 throttled_max_actions_per_minute: int = 10):
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.throttled_max_actions_per_minute = throttled_max_actions_per_minute
        self._last_cpu = time.process_time()

    def _cpu_used(self) -> float:
        now = time.process_time()
        used = now - self._last_cpu
        self._last_cpu = now
        return used

    def _memory_used_mb(self) -> float:
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

    def strained(self) -> bool:
        if self.cpu_threshold is not None and self._cpu_used() > self.cpu_threshold:
            return True
        if self.memory_threshold is not None and self._memory_used_mb() > self.memory_threshold:
            return True
        return False

    def recommended_rate_limit(self, base: int) -> int:
        """The action budget for this cycle: the normal one, or the
        throttled one if the body is under strain."""
        if self.strained():
            return min(base, self.throttled_max_actions_per_minute)
        return base
