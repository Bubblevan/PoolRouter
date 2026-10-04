from __future__ import annotations

import httpx

from poolrouter.config import Settings
from poolrouter.runtime.models import Deployment


def provider_key(settings: Settings, provider: str) -> str:
    return settings.groq_api_key if provider == "groq" else settings.openrouter_api_key


async def post_response(client: httpx.AsyncClient, settings: Settings, target: Deployment,
                        payload: dict) -> httpx.Response:
    body = dict(payload)
    body["model"] = target.model
    body["store"] = False
    headers = {"Authorization": f"Bearer {provider_key(settings, target.provider)}",
               "Content-Type": "application/json"}
    return await client.post(f"{target.base_url}/responses", headers=headers, json=body)


def strip_reasoning(body: dict) -> dict:
    """Responses reasoning is private chain-of-thought; never relay it."""
    safe = dict(body)
    safe["output"] = [item for item in body.get("output", []) if item.get("type") != "reasoning"]
    if safe.get("output_text") is None:
        text = []
        for item in safe["output"]:
            if item.get("type") == "message":
                text.extend(c.get("text", "") for c in item.get("content", [])
                            if c.get("type") == "output_text")
        if text:
            safe["output_text"] = "".join(text)
    return safe


def semantic_response_ok(body: dict) -> bool:
    for item in body.get("output", []):
        if item.get("type") == "function_call" and item.get("arguments") is not None:
            return True
        if item.get("type") == "message" and any(
            c.get("type") == "output_text" and c.get("text") for c in item.get("content", [])
        ):
            return True
    return False
