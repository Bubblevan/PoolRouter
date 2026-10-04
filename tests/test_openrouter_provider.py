from __future__ import annotations

import asyncio
import httpx

from poolrouter.config import Settings
from poolrouter.providers.openrouter import OpenRouterProvider


def test_openrouter_key_check_reads_only_is_free_tier():
    def handler(request):
        assert request.url.path == "/api/v1/key"
        return httpx.Response(200, json={"data": {"is_free_tier": True,
            "creator_user_id": "must-not-be-persisted", "label": "private-label"}})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenRouterProvider(Settings("local", openrouter_api_key="secret"), client)
            assert await provider.eligible() is True
            assert provider._free_tier_verified is True
            assert not hasattr(provider, "creator_user_id")
    asyncio.run(run())


def test_openrouter_catalog_requires_both_zero_prices_and_text_modality():
    def handler(request):
        if request.url.path == "/api/v1/key":
            return httpx.Response(200, json={"data": {"is_free_tier": True}})
        return httpx.Response(200, json={"data": [
            {"id": "free/text", "pricing": {"prompt": "0", "completion": "0"},
             "architecture": {"modality": "text->text"}},
            {"id": "paid/text", "pricing": {"prompt": "0", "completion": "0.1"},
             "architecture": {"modality": "text->text"}},
            {"id": "free/image", "pricing": {"prompt": "0", "completion": "0"},
             "architecture": {"modality": "text+image->text"}},
        ]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = OpenRouterProvider(Settings("local", openrouter_api_key="secret"), client)
            assert await provider.free_models() == [{"id": "free/text", "input_price": 0, "output_price": 0}]
    asyncio.run(run())
