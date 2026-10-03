# ADR 0003: Provider evidence model

- Status: Accepted for M0/M1 planning
- Date: 2026-10-04

## Context

Provider policies and model prices change. A model appearing in an API catalog proves availability only. FreeRouter stores a short `free_basis` and `free_basis_checked` in its provider schema (`FreeRouter/freerouter/registry.py:107-166`) and requires listing providers to supply an allowlist or explicitly mark their whole catalog free. Its discovery module applies provider-defined listing and pricing filters (`discovery.py:46-108`, `:159-205`). These are useful foundations but do not express PoolRouter's required evidence freshness, claim, privacy, and billing controls.

## Decision

Keep provider definitions, model definitions, and evidence records separate under `registry/providers/`, `registry/models/`, and `registry/evidence/`. An admitted provider/model must carry:

- official source URL and source type;
- extracted claim and applicable provider/model scope;
- `checked_at`, expiry/recheck date, and confidence;
- lifecycle and pricing/modality basis;
- quota scope and reset behavior;
- privacy/data class and provider data-use policy;
- billing guard decision.

Catalog discovery modes are `priced_catalog`, `model_listing`, `static_official`, and `manual`. `model_listing` never establishes free status by itself. Passive runtime outcomes may update health, but they cannot extend expired free evidence. Probes are limited to new, stale, and quarantined models. Probe and traffic outcomes must distinguish throttling, quota exhaustion, paid-required, model-not-found, and transient capacity.

## Consequences

Evidence freshness is independently reviewable from runtime health. Provider policy can be paused when evidence expires without treating a healthy endpoint as free. The registry becomes more detailed than FreeRouter's current provider YAML, while discovery and traffic-based probing retain their useful cost-saving architecture.

M0 records the schemas and admission rules, but does not populate live official source URLs. Provider verification is a blocker before enabling M1 routes.
