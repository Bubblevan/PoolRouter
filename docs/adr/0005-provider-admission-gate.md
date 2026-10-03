# ADR 0005: Evidence-backed provider admission

Status: Accepted for M0.5  
Date: 2026-10-04

## Decision

Provider records are validated against `registry/schema/provider.schema.json`. Every evidence item has one typed claim (`pricing`, `quota`, `billing`, `terms`, `privacy`, `model_catalog`, `capability`, `retirement`, or `promotion`), authority, confidence, source URL, date, and refresh interval. Pricing does not prove billing safety; quota does not prove privacy; a catalog listing does not prove a free model.

Evidence freshness defaults cap the declared refresh interval: pricing/model availability and quota 7 days, promotion 1 day, billing 14 days, privacy and terms 30 days. Stale or absent official pricing, billing, terms, or privacy prevents new free admission. Secondary evidence and user assertions cannot satisfy official evidence requirements. User assertions can establish account-specific facts, but remain explicitly `USER_ASSERTED`.

The registry keeps three independent flags: `price_free` (zero nominal price for the request), `allowance_free` (finite recurring quota), and `possible_auto_charge` (risk of paid overage). Billing risk requires a hard local quota guard before admission. Dynamic catalogs require concrete model evidence and current zero input and output price; aliases do not bypass model-level checks.

## Seed decisions

- **Groq:** `FREE_ALLOWANCE`, default candidate. Free-to-Developer requires a valid payment method and explicit tier upgrade. Quotas are organization-scoped; keys do not multiply them. The account tier and exact limits remain account/runtime facts.
- **OpenRouter:** `FREE_ALLOWANCE`, default candidate subject to concrete model price checks. The reviewed Free plan describes 50 requests/day and no payment options. Free-tier privacy lacks the higher-tier Data Policy-Based Routing feature; generic `openrouter/free` is public-only, while private code needs a verified concrete upstream privacy policy.
- **Cloudflare Workers AI:** `FREE_ALLOWANCE`, disabled/conditional. Workers Free provides 10,000 Neurons/day and fails on overage; Workers Paid bills overage. A plan assertion is not verified metadata. No local Neuron guard exists, so paid/unknown accounts fail closed. The model registry includes the verified paid-only `@cf/zai-org/glm-5.3` example and is explicitly non-exhaustive.
- **Mistral Studio:** `EVAL_ONLY`, opt-in, default disabled. Free mode needs no card and has included limits, but pay-as-you-go can extend usage. Regional terms and product data settings vary; require business terms, explicit training opt-out, and local overage stop before any future use.

These records authorize no API traffic. A later runtime must perform admission before exposing deployments to LiteLLM routing.

The LiteLLM core SDK remains the provider compatibility layer. M0 assumed use of LiteLLM Proxy; M0.5 corrects that assumption because the v1.103.2 `proxy` extra depends on a separate enterprise package. PoolRouter will own the local HTTP API layer and will not install that extra.

## Validation

The offline admission helper is policy validation only. It performs no network requests and handles no credentials. Tests cover source authority, freshness, billing guards, lifecycle, Cloudflare model denials, Mistral defaults, and schema validity.
