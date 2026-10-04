from __future__ import annotations

import re
from dataclasses import asdict, dataclass


FALLBACK_CATEGORIES = {"RATE_LIMIT", "QUOTA_EXHAUSTED", "CAPACITY", "TIMEOUT", "UPSTREAM_5XX", "DEGRADED_RESPONSE"}


@dataclass
class ProviderFailure(Exception):
    provider: str
    model: str
    http_status: int | None
    provider_code: str | None
    category: str
    retryable: bool
    retry_after: str | None
    safe_message: str

    def as_dict(self) -> dict:
        return asdict(self)


def normalize_failure(provider: str, model: str, status: int | None, code: str | None = None,
                      message: str = "Upstream request failed", retry_after: str | None = None) -> ProviderFailure:
    signal = f"{code or ''} {message}".lower()
    category = ("TIMEOUT" if status is None else
                "AUTH" if status in {401, 403} else
                "QUOTA_EXHAUSTED" if status == 429 and any(w in signal for w in ("quota", "daily", "requests_per_day", "rpd")) else
                "RATE_LIMIT" if status == 429 else
                "CAPACITY" if status == 529 or any(w in signal for w in ("capacity", "overloaded")) else
                "BAD_REQUEST" if status == 400 else
                "MODEL_NOT_FOUND" if status == 404 else
                "UPSTREAM_5XX" if status >= 500 else "UNKNOWN")
    text = re.sub(r"(?i)(bearer\s+)[^\s,;]+", r"\1[REDACTED]", message)
    text = re.sub(r"(?i)(api[_ -]?key|token)[=: ]+[^\s,;]+", r"\1=[REDACTED]", text)
    text = re.sub(r"(?:gsk_[A-Za-z0-9_-]{12,}|sk-or-v1-[A-Za-z0-9_-]{12,})", "[REDACTED]", text)
    safe_code = re.sub(r"(?:gsk_[A-Za-z0-9_-]{12,}|sk-or-v1-[A-Za-z0-9_-]{12,})", "[REDACTED]", code or "")[:80] or None
    return ProviderFailure(provider, model, status, safe_code, category,
                           category in FALLBACK_CATEGORIES - {"DEGRADED_RESPONSE"},
                           retry_after, text[:240])
