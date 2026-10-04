from __future__ import annotations

from collections import deque
from time import monotonic


class QuotaLedger:
    """Conservative process-local request ledger; failed upstream attempts count."""
    def __init__(self) -> None:
        self._openrouter: deque[float] = deque()
        self._groq_remaining: dict[str, int] = {}

    def can_attempt(self, provider: str) -> bool:
        self._expire_openrouter()
        return provider != "openrouter" or len(self._openrouter) < 50

    def record_attempt(self, provider: str) -> None:
        if provider == "openrouter":
            self._expire_openrouter()
            self._openrouter.append(monotonic())

    def _expire_openrouter(self) -> None:
        cutoff = monotonic() - 86400
        while self._openrouter and self._openrouter[0] < cutoff:
            self._openrouter.popleft()

    def observe_groq_headers(self, headers: dict[str, str]) -> None:
        for name in ("x-ratelimit-remaining-requests", "x-ratelimit-remaining-tokens"):
            value = headers.get(name)
            if value and value.isdigit():
                self._groq_remaining[name] = int(value)

    def groq_remaining(self) -> dict[str, int]:
        return dict(self._groq_remaining)
