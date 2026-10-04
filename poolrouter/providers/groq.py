from __future__ import annotations

from pathlib import Path
import yaml

from poolrouter.config import Settings
from registry.policy import can_admit_free, evidence_confidence, is_fresh, load_provider


class GroqProvider:
    name = "groq"
    base_url = "https://api.groq.com/openai/v1"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def eligible(self) -> bool:
        if not self.settings.groq_api_key or self.settings.groq_account_tier != "free":
            return False
        try:
            root = Path(__file__).resolve().parents[2]
            provider = load_provider(root / "registry/providers/groq.yaml")
            catalog = yaml.safe_load((root / "registry/models/groq.yaml").read_text(encoding="utf-8"))
            entry = next(m for m in catalog["models"] if m["id"] == "openai/gpt-oss-20b")
            evidence = [e for e in entry["evidence"] if e["type"] in {"quota", "capability", "pricing"}]
            fresh = bool(evidence) and all(e["authority"] == "official"
                and evidence_confidence(e) == "OFFICIAL_CURRENT" and is_fresh(e) for e in evidence)
            model = {"concrete_model": True, "free_plan_eligible": entry["free_plan_eligible"],
                     "evidence_confidence": "OFFICIAL_CURRENT", "evidence_fresh": fresh}
            return can_admit_free(provider, model=model,
                account_assertions={"account_tier_is_free": self.settings.groq_account_tier})[0]
        except (OSError, KeyError, StopIteration, ValueError, TypeError):
            return False
