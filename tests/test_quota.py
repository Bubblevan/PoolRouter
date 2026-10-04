from poolrouter.runtime.quota import QuotaLedger
from poolrouter.transports.chat_litellm import _REQUEST_PROVIDER, _RESPONSE_QUOTA_HEADERS, _capture_quota_headers
import asyncio
import httpx


def test_openrouter_local_ledger_caps_a_rolling_day_and_counts_failed_attempts():
    quota = QuotaLedger()
    for _ in range(50):
        assert quota.can_attempt("openrouter")
        quota.record_attempt("openrouter")
    assert not quota.can_attempt("openrouter")
    assert quota.can_attempt("groq")


def test_groq_header_observation_keeps_only_selected_quota_dimensions():
    quota = QuotaLedger()
    quota.observe_groq_headers({
        "x-ratelimit-remaining-requests": "12",
        "x-ratelimit-remaining-tokens": "345",
        "set-cookie": "ignored",
        "x-ratelimit-reset-requests": "10s",
    })
    assert quota.groq_remaining() == {
        "x-ratelimit-remaining-requests": 12,
        "x-ratelimit-remaining-tokens": 345,
    }


def test_litellm_http_hook_captures_only_selected_groq_headers():
    async def run():
        response = httpx.Response(200, headers={
            "x-ratelimit-remaining-requests": "12",
            "x-ratelimit-remaining-tokens": "345",
            "x-ratelimit-limit-requests": "1000",
            "set-cookie": "ignored",
        }, request=httpx.Request("POST", "https://api.groq.com"))
        token = _REQUEST_PROVIDER.set("groq")
        try:
            await _capture_quota_headers(response)
            assert _RESPONSE_QUOTA_HEADERS.get() == {
                "x-ratelimit-remaining-requests": "12",
                "x-ratelimit-remaining-tokens": "345",
            }
        finally:
            _REQUEST_PROVIDER.reset(token)
    asyncio.run(run())
