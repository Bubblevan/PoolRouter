from __future__ import annotations

from typing import Any

from poolrouter.config import Settings
from poolrouter.runtime.models import Deployment


def provider_key(settings: Settings, provider: str) -> str:
    return settings.groq_api_key if provider == "groq" else settings.openrouter_api_key


async def chat_completion(settings: Settings, target: Deployment, payload: dict[str, Any]):
    import litellm

    clean = {k: v for k, v in payload.items() if k not in {"model", "stream"}}
    response = await litellm.acompletion(
        model=target.litellm_model,
        api_base=target.base_url,
        api_key=provider_key(settings, target.provider),
        messages=payload["messages"],
        stream=bool(payload.get("stream", False)),
        num_retries=0,
        max_retries=0,
        **{k: v for k, v in clean.items() if k != "messages"},
    )
    return response
