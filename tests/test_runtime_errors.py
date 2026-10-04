from poolrouter.runtime.errors import normalize_failure


def test_quota_error_is_distinguished_and_fallback_eligible():
    failure = normalize_failure("openrouter", "openrouter/free", 429, "daily_quota_exhausted",
                               "Free daily quota exceeded")
    assert failure.category == "QUOTA_EXHAUSTED"
    assert failure.retryable is True


def test_provider_tokens_are_redacted_from_safe_message():
    failure = normalize_failure("groq", "openai/gpt-oss-20b", 401, "invalid_api_key",
                               "Invalid credential gsk_12345678901234567890")
    assert "gsk_" not in failure.safe_message
    assert failure.category == "AUTH"
