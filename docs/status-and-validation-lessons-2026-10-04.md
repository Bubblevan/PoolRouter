# PoolRouter status and provider-validation lessons — 2026-10-04

This is the repository's consolidated status at the end of the M1A and direct-provider smoke-test work. Live provider calls below were made with synthetic public prompts and the local `.env`. Credentials and raw provider response bodies are not included.

## Repository and runtime status

M1A's local OpenAI-compatible gateway is implemented for Groq and OpenRouter. It binds to `127.0.0.1:4000`, requires the local `POOLROUTER_API_KEY`, and requires inference requests to declare `X-PoolRouter-Data-Class: public`. It supports Chat Completions and native Responses, streaming, function calls, quota/admission checks, normalized safe errors, and bounded fallback. The aliases are `free-public`, `groq-free`, and `openrouter-free`. There is no private-data route or paid fallback.

M1A changes are currently on local `main` in these reviewable commits:

| Commit | Change |
|---|---|
| `a35a34a` | M1A provider-admission and native Responses evidence |
| `5defc03` | Groq/OpenRouter local gateway |
| `33aa39d` | M1A regression suite and offline CI |

The prior live-gateway record reports 34 passing credential-free tests and the manual provider matrix. The suite was not rerun for this documentation-only update. CI is configured in `.github/workflows/tests.yml`; live provider checks remain manual and must not run in CI.

Cloudflare has direct API smoke evidence but is not an M1A runtime provider. Its local Neuron guard and admission integration remain M1B work. The additional providers below were tested directly; none has been added to PoolRouter's runtime aliases or registry admission policy.

## Provider inventory and latest result

The local `.env` contained provider credential variable names for ten providers: `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `CLOUDFLARE_API_TOKEN`, `GLM_API_KEY`, `SILICONFLOW_API_KEY`, `CEREBRAS_API_KEY`, `MODELSCOPE_ACCESS_TOKEN`, `GEMINI_API`, `NVIDIA_API_KEY`, and `OPENCODE_ZEN_API_KEY`. This list is names only; the local file remains ignored and its values are not copied into the repository.

| Provider | Current evidence / smoke outcome | PoolRouter status |
|---|---|---|
| Groq | Direct `openai/gpt-oss-20b` chat returned non-empty output. Gateway Chat, Responses, streaming, tools, and forced fallback are recorded in the M1A evidence. | M1A runtime; `FREE_ALLOWANCE` only with the configured Free-tier assertion and current admission checks. |
| OpenRouter | `openrouter/free` and a concrete zero-price model returned non-empty output. Gateway Chat, Responses, streams, tools, and runtime key free-tier checks are recorded. | M1A runtime; free route is public/synthetic-only and must recheck account/model state. |
| Cloudflare Workers AI | Direct account catalog/model smoke returned non-empty output from `@cf/meta/llama-3.2-1b-instruct`. | No runtime route. `FREE_ALLOWANCE`, conditional on actual Free plan and local Neuron guard; M1B remains open. |
| BigModel / Zhipu | Official docs list `glm-4.7-flash`; direct chat returned HTTP 429 with no reply. | Not runtime-admitted; live availability/quota unresolved. |
| Cerebras | Authenticated model catalog returned HTTP 200. Current pricing lists the sample Qwen 3.8 27B model as paid; no inference call was made. | No runtime route; do not label its promotional credit as a free model or allowance. |
| SiliconFlow | Current official pricing marks `XingChenAGI/Xing4.0-29B` input/output zero-priced; it is in the authenticated catalog. Chat returned HTTP 200 and non-empty output after increasing `max_tokens` to 128. | Direct smoke verified only; no runtime policy/adapter. Pricing must stay catalog-driven. |
| ModelScope | Current account catalog included the supplied Qwen 3.5 IDs; `Qwen/Qwen3.5-35B-A3B` Chat Completions returned HTTP 200 and non-empty output. | Direct smoke verified only; current quota and long-term free allocation remain unproven; Responses API not tested. |
| Gemini Developer API | Model directory returned HTTP 200. `gemini-3.8-flash` and `gemini-3.5-flash` inference returned 403; `gemini-2.5-flash` returned 404. | No runtime route; catalog visibility did not establish account entitlement. Free-tier account eligibility is unresolved. |
| NVIDIA NIM | Current Build catalog marks `nvidia/nemotron-3.5-lightning-30b-a3b` a free development endpoint; chat returned HTTP 200 and non-empty output. | No runtime route. Keep in `EVAL_ONLY`, not the normal `free-*` pool; send synthetic/public data only. |
| OpenCode Zen | Two current listed free models returned HTTP 403. | No runtime route. Keep as `PROMOTION`; model availability and price are temporary, and access is unresolved. |

The earlier baseline also tracks Mistral, Alibaba Model Studio, Baidu Qianfan, GitHub Models, and other candidates. They are not among the ten provider credential variables found in this `.env` inspection and have no live result in this smoke-test round. See `docs/provider-policy.md` for lifecycle policy and outstanding candidates.

## What the tests actually prove

- A successful `/models` response proves catalog visibility, not free pricing, inference entitlement, or a valid free quota.
- An HTTP 200 inference response is not semantic success by itself. Require non-empty assistant text, a valid tool call, or the expected structured result. SiliconFlow returned an empty message with a small output cap before a larger cap produced text.
- A `:free` suffix, “free endpoint” badge, or provider-wide free tier is not enough to admit a concrete deployment. Check the exact model's current input/output price, modalities, account eligibility, billing tier, quota and data-use terms.
- Free categories are different: `PERMANENT_FREE`/zero model price, finite `FREE_ALLOWANCE`, paid service with promotional credit, and trial/evaluation access must not be collapsed into one policy.
- The endpoint and wire protocol are provider-specific even when OpenAI-compatible. Verify the exact URL, model identifier, auth header, body fields, and semantic response shape using a tiny synthetic prompt.
- Treat status codes as evidence, not diagnoses. The BigModel 429 and OpenCode/Gemini 403 results were retained without raw bodies; their exact causes remain unknown. Avoid guessing based on a generic code.
- Keep retries bounded. Trying another currently listed zero-price candidate can distinguish model availability from provider access, but stop after a small number of failures instead of burning quota.
- Keep catalog discovery read-only until a zero-price or no-charge basis is established. Cerebras was not sent inference traffic because the current sample model is priced. Do not let promotional credits silently substitute for a no-cost guarantee.
- Use synthetic/public prompts only during provider validation. Some free/evaluation endpoints may log requests or use them for service/model improvement.
- Keep evidence sanitized: record provider, model, endpoint shape, HTTP status, semantic pass/fail and only safe error codes. Never persist authorization headers, keys, account IDs, raw error bodies, or private prompts/generated content. Existing historical evidence retains only synthetic public greetings and their harmless example replies.
- Direct provider probes and PoolRouter runtime tests answer different questions. A direct HTTP success does not prove the adapter, policy admission, proxy, fallback, or stream behavior is implemented; only the Groq/OpenRouter M1A gateway has that runtime evidence.

## Recommended next work

1. Resolve BigModel rate-limit/entitlement status and Gemini/OpenCode access failures using provider dashboards or fresh account-level evidence; do not infer the cause from the catalog.
2. For ModelScope, establish current quota, billing behavior after any free allowance, and whether a local stop can prevent charges before considering runtime admission. The one successful smoke call proves API functionality, not that the current account's use is permanently free.
3. Add SiliconFlow only after its live pricing catalog can be represented and checked at admission; its zero-price row is dynamic evidence, not a permanent allowlist.
4. Keep NVIDIA in a separately opt-in evaluation pool with its logging/privacy constraints. Keep OpenCode promotion models separate from permanent/free allowances.
5. Reconsider Cerebras only if a current, explicit zero-cost allowance/model becomes available or the owner opts into paid/promotional-credit use with a hard spend limit.
6. Implement Cloudflare M1B's local Neuron guard before enabling any runtime route.

## Evidence files

- `docs/evidence/manual-provider-smoke-test-2026-10-04.md` — Groq, OpenRouter and Cloudflare direct smoke tests.
- `docs/evidence/native-responses-contract-2026-10-04.md` — Groq/OpenRouter native Responses contracts.
- `docs/evidence/live-gateway-smoke-2026-10-04.md` — M1A gateway runtime matrix and offline suite result.
- `docs/evidence/additional-provider-smoke-test-2026-10-04.md` — additional direct provider calls, status codes and sanitized request shapes.
- `docs/evidence/provider-evidence-2026-10-04.md` and `docs/provider-policy.md` — evidence registry snapshot and lifecycle policy.
