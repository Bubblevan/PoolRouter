from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Deployment:
    provider: str
    model: str
    base_url: str
    litellm_model: str
    alias: str
    data_class: str = "public"


ALIASES = {
    "free-public": ("groq", "openrouter"),
    "groq-free": ("groq",),
    "openrouter-free": ("openrouter",),
}

def deployment(provider: str, alias: str) -> Deployment:
    if provider == "groq":
        model = "openai/gpt-oss-20b"
        return Deployment(provider, model, "https://api.groq.com/openai/v1",
                          f"groq/{model}", alias)
    model = "openrouter/free"
    return Deployment(provider, model, "https://openrouter.ai/api/v1",
                      f"openrouter/{model}", alias)
