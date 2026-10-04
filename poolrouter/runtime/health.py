from __future__ import annotations

from collections import defaultdict


class Health:
    """Small process-local rolling failure state; one empty response never quarantines."""
    def __init__(self) -> None:
        self.failures: dict[str, int] = defaultdict(int)
        self.quarantined: set[str] = set()

    def record(self, provider: str, healthy: bool) -> None:
        if healthy:
            self.failures[provider] = 0
            self.quarantined.discard(provider)
        else:
            self.failures[provider] += 1
            if self.failures[provider] >= 3:
                self.quarantined.add(provider)
