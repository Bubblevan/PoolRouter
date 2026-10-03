"""Offline evidence and admission checks; this module never calls a provider."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import json
import yaml

ROOT = Path(__file__).resolve().parents[1]
FRESHNESS_DAYS = {
    "pricing": 7, "model_catalog": 7, "quota": 7, "promotion": 1,
    "billing": 14, "privacy": 30, "terms": 30,
    "capability": 30, "retirement": 30,
}
ROUTABLE_LIFECYCLES = {"PERMANENT_FREE", "FREE_ALLOWANCE"}


def load_provider(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def is_fresh(evidence: dict[str, Any], today: date | None = None) -> bool:
    today = today or date.today()
    checked = evidence.get("checked_at")
    if isinstance(checked, date):
        checked = checked
    else:
        checked = date.fromisoformat(str(checked))
    age = (today - checked).days
    max_age = min(evidence["refresh_after_days"], FRESHNESS_DAYS[evidence["type"]])
    return 0 <= age <= max_age


def evidence_confidence(e: dict[str, Any]) -> str:
    """Derive stale confidence at read time; preserve source confidence in YAML."""
    if e.get("confidence") == "OFFICIAL_CURRENT" and not is_fresh(e):
        return "OFFICIAL_STALE"
    return e.get("confidence", "UNKNOWN")


def has_fresh_official(provider: dict[str, Any], types: set[str]) -> bool:
    return all(any(e["type"] == kind and e["authority"] == "official"
                   and evidence_confidence(e) == "OFFICIAL_CURRENT"
                   for e in provider["evidence"]) for kind in types)


def can_admit_free(provider: dict[str, Any], *, model: dict[str, Any] | None = None,
                   account_assertions: dict[str, str] | None = None,
                   today: date | None = None) -> tuple[bool, str]:
    if provider.get("lifecycle") not in ROUTABLE_LIFECYCLES:
        return False, "lifecycle is not routable"
    admission = provider["admission"]
    if not admission["free_pool"] or not admission["default_enabled"]:
        return False, "provider is not default-enabled for free pool"
    billing = provider["billing"]
    if billing["possible_auto_charge"] and not billing["hard_local_quota_guard"]:
        return False, "possible charge lacks hard local quota guard"
    required = {"pricing", "billing", "terms", "privacy"}
    if not has_fresh_official(provider, required):
        return False, "missing or stale official evidence"
    for condition in billing["conditional_on"] + admission.get("requires", []):
        if condition in {"account_tier_is_free", "free_account_plan", "CLOUDFLARE_WORKERS_PLAN=free"}:
            assertion_key = {
                "account_tier_is_free": "account_tier_is_free",
                "free_account_plan": "free_account_plan",
                "CLOUDFLARE_WORKERS_PLAN=free": "CLOUDFLARE_WORKERS_PLAN",
            }[condition]
            if not account_assertions or account_assertions.get(assertion_key) != "free":
                return False, f"missing USER_ASSERTED {assertion_key}=free"
        elif condition == "concrete_model_input_and_output_price_zero":
            if not model or not model.get("concrete_model") or model.get("input_price") != 0 or model.get("output_price") != 0:
                return False, "concrete model must have current zero input/output price"
            if model.get("evidence_confidence") not in {"OFFICIAL_CURRENT", "RUNTIME_OBSERVED"} or not model.get("evidence_fresh", False):
                return False, "concrete model price evidence is not current/approved"
        elif condition in {"fresh_official_evidence", "current_zero_price"}:
            continue
        elif condition in {"concrete_model", "current_model_free_availability"}:
            if not model:
                return False, "model-specific evidence required"
        elif condition == "current_model_pricing":
            if (not model or model.get("evidence_confidence") not in {"OFFICIAL_CURRENT", "RUNTIME_OBSERVED"}
                    or not model.get("evidence_fresh", False) or model.get("price_free") is not True):
                return False, "concrete model needs fresh official/runtime price evidence"
        elif condition == "hard_neuron_quota_guard":
            return False, "Cloudflare Neuron guard is not implemented"
        else:
            return False, f"unsupported admission condition: {condition}"
    if model and model.get("workers_free") is False:
        return False, "model is paid-only on Workers Free"
    return True, "eligible subject to recorded account assertions"


def validate_shipped() -> list[str]:
    from jsonschema import Draft202012Validator, FormatChecker
    schema = json.loads((ROOT / "registry/schema/provider.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors: list[str] = []
    def normalize_dates(value: Any) -> Any:
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, dict):
            return {k: normalize_dates(v) for k, v in value.items()}
        if isinstance(value, list):
            return [normalize_dates(v) for v in value]
        return value
    for path in sorted((ROOT / "registry/providers").glob("*.yaml")):
        obj = normalize_dates(load_provider(path))
        for error in validator.iter_errors(obj):
            errors.append(f"{path.name}: {error.json_path}: {error.message}")
    return errors
