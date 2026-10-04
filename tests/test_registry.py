from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
import sys

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from registry.policy import ROOT, can_admit_free, is_fresh, load_provider, validate_shipped


def provider(name):
    return load_provider(ROOT / f"registry/providers/{name}.yaml")


def test_all_shipped_provider_yaml_validates():
    assert validate_shipped() == []


def test_provider_requires_official_pricing_evidence_for_free_admission():
    p = provider("groq")
    p["evidence"] = [e for e in p["evidence"] if e["type"] != "pricing"]
    assert can_admit_free(p, account_assertions={"account_tier_is_free": "free"})[0] is False


def test_billing_risk_requires_guard():
    p = provider("cloudflare")
    p["billing"]["possible_auto_charge"] = True
    p["billing"]["hard_local_quota_guard"] = False
    assert can_admit_free(p, account_assertions={"account_plan_free": "free"})[0] is False


def test_stale_pricing_cannot_admit_provider():
    p = provider("groq")
    price = next(e for e in p["evidence"] if e["type"] == "pricing")
    price["checked_at"] = date.today() - timedelta(days=8)
    assert is_fresh(price) is False
    assert can_admit_free(p, account_assertions={"account_tier_is_free": "free"})[0] is False


def test_secondary_source_cannot_admit_provider():
    p = provider("groq")
    price = next(e for e in p["evidence"] if e["type"] == "pricing")
    price["authority"] = "secondary"
    price["confidence"] = "SECONDARY"
    assert can_admit_free(p, account_assertions={"account_tier_is_free": "free"})[0] is False


def test_eval_only_cannot_enter_free_pool():
    assert can_admit_free(provider("mistral"))[0] is False


def test_unknown_lifecycle_cannot_enter_free_pool():
    p = provider("groq")
    p["lifecycle"] = "UNKNOWN"
    assert can_admit_free(p, account_assertions={"account_tier_is_free": "free"})[0] is False


def test_user_assertion_is_not_marked_official():
    p = provider("cloudflare")
    assertion = p["account_assertions"][0]
    assert assertion["source_confidence"] == "USER_ASSERTED"
    assert all(e["confidence"] != "USER_ASSERTED" for e in p["evidence"])


def test_cloudflare_paid_only_model_not_free_admitted():
    data = yaml.safe_load((ROOT / "registry/models/cloudflare.yaml").read_text(encoding="utf-8"))
    model = data["models"][0]
    from jsonschema import Draft202012Validator, FormatChecker
    schema = __import__("json").loads((ROOT / "registry/schema/model.schema.json").read_text(encoding="utf-8"))
    schema_model = {**model, "checked_at": data["snapshot_checked_at"].isoformat(), "refresh_after_days": 7,
                    "evidence": [{**item, "checked_at": item["checked_at"].isoformat()} for item in model["evidence"]]}
    assert list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(schema_model)) == []
    model.update(concrete_model=True, evidence_confidence="OFFICIAL_CURRENT", evidence_fresh=True)
    assert model["availability"]["workers_free"] is False
    model["workers_free"] = model["availability"]["workers_free"]
    assert can_admit_free(provider("cloudflare"), model=model,
                          account_assertions={"account_plan_free": "free"})[0] is False


def test_groq_free_plan_model_record_is_well_formed_and_developer_price_is_separate():
    data = yaml.safe_load((ROOT / "registry/models/groq.yaml").read_text(encoding="utf-8"))
    model = data["models"][0]
    from jsonschema import Draft202012Validator, FormatChecker
    schema = __import__("json").loads((ROOT / "registry/schema/model.schema.json").read_text(encoding="utf-8"))
    checked = {**model, "provider": "groq", "checked_at": data["snapshot_checked_at"].isoformat(),
               "refresh_after_days": 7,
               "evidence": [{**item, "checked_at": item["checked_at"].isoformat()} for item in model["evidence"]]}
    assert list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(checked)) == []
    assert model["free_plan_eligible"] is True
    assert model["developer_list_price"] == {"input_per_million": 0.075, "output_per_million": 0.30}


def test_mistral_not_default_enabled():
    p = provider("mistral")
    assert p["admission"]["default_enabled"] is False
    assert p["admission"]["free_pool"] is False


def test_openrouter_requires_runtime_tier_check_not_operator_assertion():
    p = provider("openrouter")
    assert can_admit_free(p, account_assertions={"free_account_plan": "free"})[0] is False
    alias = {"model_id": "openrouter/free", "data_class": "public"}
    assert can_admit_free(p, model=alias, account_assertions={"is_free_tier": "true"})[0] is True


def test_groq_nonzero_list_price_can_enter_free_pool_on_verified_free_tier():
    p = provider("groq")
    model = {"concrete_model": True, "free_plan_eligible": True,
             "evidence_confidence": "OFFICIAL_CURRENT", "evidence_fresh": True,
             "input_price": 0.075, "output_price": 0.30}
    ok, reason = can_admit_free(p, model=model,
                                account_assertions={"account_tier_is_free": "free"})
    assert ok is True, reason


def test_groq_paid_account_is_not_admitted_despite_free_plan_model_entry():
    p = provider("groq")
    model = {"concrete_model": True, "free_plan_eligible": True,
             "evidence_confidence": "OFFICIAL_CURRENT", "evidence_fresh": True,
             "input_price": 0.075, "output_price": 0.30}
    assert can_admit_free(p, model=model,
                          account_assertions={"account_tier_is_free": "paid"})[0] is False


def test_openrouter_requires_runtime_free_tier_boolean():
    p = provider("openrouter")
    alias = {"model_id": "openrouter/free", "data_class": "public"}
    assert can_admit_free(p, model=alias, account_assertions={"is_free_tier": "false"})[0] is False


def test_default_freshness_windows_are_type_specific():
    p = provider("groq")
    pricing = next(e for e in p["evidence"] if e["type"] == "pricing")
    billing = next(e for e in p["evidence"] if e["type"] == "billing")
    assert pricing["refresh_after_days"] == 7
    assert billing["refresh_after_days"] == 14


def test_litellm_pin_uses_core_sdk_without_proxy_enterprise_extra():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"litellm==1.103.2"' in pyproject
    assert "litellm[proxy]" not in pyproject
