"""Per-key rate limit: a sliding one-minute window, kept in memory.

In memory is enough for the single Uvicorn worker the service runs with; more
processes would each count separately and need a shared store.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable

WINDOW_SECONDS = 60.0


class RateLimiter:
    def __init__(self, limit_per_minute: int, clock: Callable[[], float] = time.monotonic):
        self.limit = limit_per_minute
        self.clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key_id: str) -> int | None:
        """Record a request. Return None if allowed, else the seconds to wait."""
        now = self.clock()
        with self._lock:
            hits = self._hits.setdefault(key_id, deque())
            while hits and hits[0] <= now - WINDOW_SECONDS:
                hits.popleft()
            if len(hits) >= self.limit:
                return max(1, math.ceil(hits[0] + WINDOW_SECONDS - now))
            hits.append(now)
            return None
