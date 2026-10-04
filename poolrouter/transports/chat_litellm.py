from __future__ import annotations

from contextvars import ContextVar
from typing import Any

from poolrouter.config import Settings
from poolrouter.runtime.models import Deployment

_REQUEST_PROVIDER: ContextVar[str | None] = ContextVar("poolrouter_provider", default=None)
_RESPONSE_QUOTA_HEADERS: ContextVar[dict[str, str]] = ContextVar("poolrouter_quota_headers", default={})
_LITELLM_HTTP_CLIENT = None


def response_quota_headers() -> dict[str, str]:
    return dict(_RESPONSE_QUOTA_HEADERS.get())


async def _capture_quota_headers(response) -> None:
    """HTTPX response hook: retain only two Groq quota values in this request context."""
    if _REQUEST_PROVIDER.get() == "groq":
        _RESPONSE_QUOTA_HEADERS.set({name: response.headers[name] for name in (
            "x-ratelimit-remaining-requests", "x-ratelimit-remaining-tokens") if name in response.headers})


def _http_client(litellm):
    global _LITELLM_HTTP_CLIENT
    if _LITELLM_HTTP_CLIENT is None:
        from litellm.llms.custom_httpx.http_handler import AsyncHTTPHandler
        _LITELLM_HTTP_CLIENT = AsyncHTTPHandler(event_hooks={"response": [_capture_quota_headers]},
                                                client_alias="poolrouter")
    return _LITELLM_HTTP_CLIENT


async def close_chat_http_client() -> None:
    if _LITELLM_HTTP_CLIENT is not None:
        await _LITELLM_HTTP_CLIENT.client.aclose()


def provider_key(settings: Settings, provider: str) -> str:
    return settings.groq_api_key if provider == "groq" else settings.openrouter_api_key


async def chat_completion(settings: Settings, target: Deployment, payload: dict[str, Any]):
    import litellm

    _RESPONSE_QUOTA_HEADERS.set({})
    provider_token = _REQUEST_PROVIDER.set(target.provider)
    clean = {k: v for k, v in payload.items() if k not in {"model", "stream"}}
    try:
        return await litellm.acompletion(
            model=target.litellm_model,
            api_base=target.base_url,
            api_key=provider_key(settings, target.provider),
            messages=payload["messages"],
            stream=bool(payload.get("stream", False)),
            num_retries=0,
            max_retries=0,
            client=_http_client(litellm),
            **{k: v for k, v in clean.items() if k != "messages"},
        )
    finally:
        _REQUEST_PROVIDER.reset(provider_token)
