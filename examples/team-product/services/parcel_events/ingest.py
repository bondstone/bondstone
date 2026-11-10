"""Carrier scan ingestion."""

import time


# bondstone: SBB-parcel-events
class TokenBucket:
    """Keeps carrier polling under the contracted rate."""

    def __init__(self, rate_per_second: float) -> None:
        self.rate = rate_per_second * 0.8
        self.tokens = self.rate
        self.updated = time.monotonic()

    def take(self) -> bool:
        now = time.monotonic()
        self.tokens = min(self.rate, self.tokens + (now - self.updated) * self.rate)
        self.updated = now
        if self.tokens < 1:
            return False
        self.tokens -= 1
        return True
