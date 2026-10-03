# ADR 0002: Zero-cost routing invariant

- Status: Accepted for M0/M1 planning
- Date: 2026-10-04

## Context

An API key or `/models` listing does not prove that a request is free. A provider may expose paid models through the same endpoint, free allowances may expire, and a trial provider may charge after its initial balance is exhausted. A zero value in usage accounting is also not proof that no charge can occur.

FreeRouter's registry validator already prevents a bare catalog listing from being treated as a free catalog (`FreeRouter/freerouter/registry.py:154-166`). Its discovery code has useful zero-price and text-modality filters (`discovery.py:46-108`). FreeLLMAPI separately classifies retryable, payment, missing-model, and forbidden errors (`freellmapi/server/src/routes/proxy.ts:344-419`). PoolRouter makes these checks mandatory policy, not provider configuration convention.

## Decision

Every deployment admitted to a `free-*` alias must have a fresh, official free-tier evidence record; an allowed lifecycle (`PERMANENT_FREE` or `FREE_ALLOWANCE`); compatible modality and model-level pricing evidence; a known quota scope/reset; and a satisfied billing guard. Unknown or stale facts fail closed.

`TRIAL`, `PROMOTION`, and `EVAL_ONLY` deployments use separate aliases and cannot be fallback targets for `free-*`. Paid models are excluded even when hosted by a provider with a free plan. No automatic paid fallback or post-quota invocation is allowed. When no eligible free capacity remains, return `FREE_POOL_EXHAUSTED`.

Normalize provider responses into distinct categories, including `RATE_LIMIT`, `DAILY_QUOTA`, `TRIAL_EXHAUSTED`, `PAID_REQUIRED`, `MODEL_NOT_FOUND`, `CAPACITY`, and `AUTH`. A 429 is not evidence that a model is retired. A paid-required response quarantines that deployment from free routes. Provider project/account quotas remain at provider-defined scope, independent of API key count.

## Consequences

The eligible runtime deployment set is narrower than the discovered catalog. Catalog refresh may suggest candidates but cannot admit them without evidence. If billing behavior cannot be verified or guarded, PoolRouter declines to route that provider/model. The expected exhaustion mode is explicit failure, not a charge.
