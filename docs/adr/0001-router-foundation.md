# ADR 0001: Router foundation

- Status: Accepted for M0/M1 planning
- Date: 2026-10-04

## Context

PoolRouter needs OpenAI-compatible chat and Responses endpoints, provider adapters, retries, fallback, cooldown, and usage logging. Reimplementing provider SDK behavior would duplicate a large, actively maintained compatibility layer. At the same time, provider/model free status and zero-charge admission cannot be inferred from generic model support or a catalog listing.

The local references show complementary responsibilities. LiteLLM provides the proxy routes (`litellm/litellm/proxy/proxy_server.py:11949-11978`, `chat_completion`) and deployment selection/cooldown (`litellm/litellm/router.py:8563-8581`, `_get_healthy_deployments`; `:12977+`, `async_get_healthy_deployments`). FreeLLMAPI demonstrates Responses-to-chat translation (`freellmapi/server/src/routes/responses.ts:150-215`) and single-user SQLite (`server/src/db/index.ts:20-38`). FreeRouter demonstrates evidence-aware catalog filtering (`FreeRouter/freerouter/discovery.py:46-108`), traffic-informed health (`refresh.py:246-293`), and live deployment reconciliation (`refresh.py:212-244`).

## Decision

Use LiteLLM as a pinned runtime dependency for proxy protocol, provider compatibility, and generic routing reliability. Keep PoolRouter's registry, lifecycle, source evidence, privacy classes, quota scopes, billing guard, and free-alias admission as PoolRouter-owned policy. Start with SQLite. Keep the default bind on loopback and use a local master key.

Use FreeLLMAPI and FreeRouter as design references only. M0 copies no code. Any provider-specific adapter or Responses shim is added only if a supported LiteLLM path fails a concrete compatibility requirement.

## Consequences

PoolRouter avoids maintaining provider wire-format adapters and receives upstream fixes through dependency updates. It must pin and review LiteLLM versions and license boundaries. PoolRouter still owns the safety-critical decision that a deployment is eligible for a given alias; LiteLLM routing cannot broaden that eligibility set. SQLite is sufficient for local single-user metadata; Redis and Postgres are not M0 requirements.

This decision makes PoolRouter distinct from a FreeRouter fork: PoolRouter's primary differentiator is the evidence, privacy, lifecycle, and no-auto-charge admission boundary rather than catalog refresh alone.
