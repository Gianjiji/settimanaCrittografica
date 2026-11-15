"""A request budget per client address, kept in memory.

Every answer sent to the API becomes a row in the log, and the API asks for no account,
so without a ceiling one script could grow the database for as long as it liked. A
token bucket is the smallest thing that stops it: each address owns a few tokens, a
request spends one, and they come back at a steady rate. A reader working through a
fascicle never notices; a loop that posts as fast as it can runs dry within a second.

The table lives in the process: it is forgotten on restart and not shared between
workers. Both are fine for a ceiling, since the worst case is a budget that is a little
more generous than written.
"""

import threading
import time


class RateLimiter:
    def __init__(self, burst, per_second, clock=time.monotonic, max_clients=10000):
        if burst < 1 or per_second <= 0:
            raise ValueError("burst must be at least 1 and per_second positive")
        self.burst = float(burst)
        self.per_second = float(per_second)
        self.max_clients = max_clients
        self._clock = clock
        self._lock = threading.Lock()
        self._buckets = {}  # key -> [tokens, time of the last update]

    def _refill(self, bucket, now):
        elapsed = max(0.0, now - bucket[1])
        bucket[0] = min(self.burst, bucket[0] + elapsed * self.per_second)
        bucket[1] = now

    def allow(self, key):
        """Spend one token of `key`. False when the bucket is empty."""
        now = self._clock()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                if len(self._buckets) >= self.max_clients:
                    self._forget_idle(now)
                bucket = self._buckets[key] = [self.burst, now]
            else:
                self._refill(bucket, now)
            if bucket[0] < 1.0:
                return False
            bucket[0] -= 1.0
            return True

    def retry_after(self, key):
        """Whole seconds until `key` owns a token again, at least one."""
        now = self._clock()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                return 1
            self._refill(bucket, now)
            missing = max(0.0, 1.0 - bucket[0])
        return max(1, int(-(-missing // self.per_second)))

    def _forget_idle(self, now):
        """Make room, so that a flood of addresses cannot grow the table without end.

        A bucket that has had time to fill up again says nothing a fresh one would not,
        so those go first. If every bucket is still in use the oldest half goes: the
        addresses in it get a full budget back, which errs on the side of the reader.
        """
        full_after = self.burst / self.per_second
        for key in [k for k, b in self._buckets.items() if now - b[1] >= full_after]:
            del self._buckets[key]
        if len(self._buckets) >= self.max_clients:
            oldest = sorted(self._buckets, key=lambda k: self._buckets[k][1])
            for key in oldest[:max(1, len(oldest) // 2)]:
                del self._buckets[key]

    def reset(self):
        with self._lock:
            self._buckets.clear()
