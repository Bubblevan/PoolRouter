from __future__ import annotations

from poolrouter.config import Settings
from poolrouter.providers.groq import GroqProvider
from poolrouter.providers.openrouter import OpenRouterProvider
from poolrouter.runtime.models import ALIASES, Deployment, deployment
from poolrouter.runtime.planner import providers_for_alias


class Admission:
    def __init__(self, settings: Settings, openrouter: OpenRouterProvider) -> None:
        self.groq = GroqProvider(settings)
        self.openrouter = openrouter

    async def candidates(self, alias: str, data_class: str) -> list[Deployment]:
        if alias not in ALIASES:
            return []
        if data_class != "public":
            return []
        eligible: list[Deployment] = []
        for provider in providers_for_alias(alias):
            if provider == "groq" and self.groq.eligible():
                eligible.append(deployment(provider, alias))
            elif provider == "openrouter" and await self.openrouter.eligible():
                eligible.append(deployment(provider, alias))
        return eligible
