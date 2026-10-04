from __future__ import annotations

from pathlib import Path
from decimal import Decimal, InvalidOperation

import httpx

from poolrouter.config import Settings
from registry.policy import can_admit_free, load_provider


class OpenRouterProvider:
    name = "openrouter"
    base_url = "https://openrouter.ai/api/v1"

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings, self.client = settings, client
        self._free_tier_verified = False

    async def eligible(self) -> bool:
        if not self.settings.openrouter_api_key:
            return False
        try:
            response = await self.client.get(f"{self.base_url}/key", headers={
                "Authorization": f"Bearer {self.settings.openrouter_api_key}"})
            if response.status_code != 200:
                return False
            self._free_tier_verified = response.json().get("data", {}).get("is_free_tier") is True
            if not self._free_tier_verified:
                return False
            provider = load_provider(Path(__file__).resolve().parents[2] / "registry/providers/openrouter.yaml")
            return can_admit_free(provider, model={"model_id": "openrouter/free", "data_class": "public"},
                                  account_assertions={"is_free_tier": "true"})[0]
        except (httpx.HTTPError, OSError, AttributeError, KeyError, ValueError, TypeError):
            return False

    async def free_models(self) -> list[dict]:
        """Return a minimal projection of current zero-priced text models."""
        if not await self.eligible():
            return []
        try:
            response = await self.client.get(f"{self.base_url}/models", headers={
                "Authorization": f"Bearer {self.settings.openrouter_api_key}"})
            response.raise_for_status()
            result = []
            for model in response.json().get("data", []):
                pricing = model.get("pricing", {})
                architecture = model.get("architecture", {})
                try:
                    free = (Decimal(str(pricing.get("prompt"))) == 0
                            and Decimal(str(pricing.get("completion"))) == 0)
                except (InvalidOperation, TypeError):
                    free = False
                if (model.get("id") and free
                        and architecture.get("modality") == "text->text"):
                    result.append({"id": model["id"], "input_price": 0, "output_price": 0})
            return result
        except (httpx.HTTPError, AttributeError, ValueError, TypeError):
            return []
