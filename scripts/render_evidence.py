from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from registry.policy import load_provider

root = Path(__file__).resolve().parents[1]
rows = []
for path in sorted((root / "registry/providers").glob("*.yaml")):
    p = load_provider(path)
    ev = p["evidence"]
    sources = "<br>".join(f"[{e['id']}]({e['url']})" for e in ev if e["authority"] == "official")
    questions = {
        "groq": "Confirm account tier is Free; read exact organization/model limits and selected Data Controls before enabling.",
        "openrouter": "Recheck each concrete model price and upstream logging/training policy; keep generic free alias public-only.",
        "cloudflare": "Account plan is a user assertion; implement local Neuron guard before any Workers Paid or unknown plan route. Paid-only snapshot is not exhaustive.",
        "mistral": "Regional terms vary; require business scope, product-specific training opt-out and a local stop before pay-as-you-go overage.",
    }[p["id"]]
    privacy = f"public={p['privacy']['public_code']}; private={p['privacy']['private_code']}; sensitive={p['privacy']['sensitive_data']}"
    terms = p["legal"]["intended_use"]
    rows.append(f"| {p['display_name']} | `{p['lifecycle']}` | {p['admission']['default_enabled']} (conditional={p['admission'].get('conditional', False)}) | {p['billing']['zero_cost_basis']} | {p['quota']['scope']} | {p['billing']['possible_auto_charge']} | {privacy} | {terms} | 2026-10-04 | {sources} | {questions} |")

doc = """# Provider evidence snapshot — 2026-10-04

Generated from `registry/providers/*.yaml` by `python scripts/render_evidence.py`. Evidence links are official provider sources; this snapshot records claims checked on the date shown and does not make provider requests.

| Provider | Lifecycle | Default route | Zero-cost basis | Quota scope | Auto-charge risk | Privacy | Terms/use restriction | Last verified | Official sources | Open questions |
|---|---|---|---|---|---|---|---|---|---|---|
""" + "\n".join(rows) + "\n\n" + """## Price, allowance, and billing are separate

- `PRICE_FREE`: a concrete model request has zero nominal inference price. Dynamic model prices must be checked at admission and rechecked while routed.
- `ALLOWANCE_FREE`: an account has a finite free quota or included usage. This says nothing by itself about overage billing.
- `BILLING_SAFE`: exhausting the allowance cannot create a charge under the configured account state and guard.

Cloudflare demonstrates the distinction: its Workers Free plan has a finite daily allowance and fails on exhaustion; Workers Paid has the same included allowance but charges for overage. Cloudflare records `price_free: false`, `allowance_free: true`, and `possible_auto_charge: true`; admission remains closed until the plan is asserted Free and a local Neuron guard exists. A user assertion is not provider-verified evidence.

Groq and OpenRouter account conditions, exact quotas, concrete model prices, and provider-side data policies still require runtime/configuration checks. This file is evidence inventory, not permission to send traffic.
"""
out = root / "docs/evidence/provider-evidence-2026-10-04.md"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(doc, encoding="utf-8")
