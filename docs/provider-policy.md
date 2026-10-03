# Provider policy baseline

Baseline date: 2026-10-04. This file records the user-supplied requirements baseline for M0. It does not claim that current official terms, prices, quotas, or model availability have been independently verified. Evidence is required before runtime admission.

| Provider | Lifecycle | Initial state | PoolRouter policy |
|---|---|---|---|
| Groq | `FREE_ALLOWANCE` | Enabled candidate | Per-model limits; require current official Free Plan evidence and provider terms before M1 admission. |
| Cloudflare Workers AI | `FREE_ALLOWANCE` | Enabled candidate | Per-model admission. Exclude paid-only models. Distinguish daily allowance exhaustion, capacity, and paid-required errors. |
| OpenRouter | `FREE_ALLOWANCE` | Enabled candidate | Admit only available models with zero input and output token price and no hidden modality charge. One account, private use, no resale. |
| Mistral Studio | `FREE_ALLOWANCE` | Enabled candidate | Verify authenticated model availability and current Free mode evidence. |
| Gemini API | `FREE_ALLOWANCE` | Opt-in, disabled by default | Require explicit user enablement. Surface developer/professional-use scope and free-tier data policy. Exclude sensitive requests unless separately authorized by the privacy policy. |
| ModelScope API Inference | `UNKNOWN` candidate | Disabled pending current evidence | Implement only after fresh official allocation evidence and a current probe. The old 2,000 calls/day announcement is insufficient by itself. |
| Baidu Qianfan | `UNKNOWN` candidate | Disabled pending current evidence | Confirm current official pricing for candidate ERNIE models before admission. |
| SiliconFlow | `UNKNOWN` | Disabled | Do not infer current free status from another catalog. |
| BigModel / Z.ai | `UNKNOWN` | Disabled | Do not infer current free status from another catalog. |
| Alibaba Model Studio | `TRIAL` | Separate trial pool only | Must stop at free quota. Never enters `free-*`; disable if post-quota pay-as-you-go cannot be prevented. |
| OpenCode Zen | `PROMOTION` | Separate promotion pool only | Keep temporary zero-price models out of `free-*`. Recheck price and expiration. |
| NVIDIA NIM | `EVAL_ONLY` | Separate evaluation pool only | Respect evaluation scope. Never enters `free-*`. |
| Cerebras | `UNKNOWN` | Disabled pending current evidence | Classify only after current evidence review. |
| GitHub Models | `RETIRED` | Never route | Retired per supplied baseline; require a new explicit review to change this state. |

`Enabled candidate` is not permission to route yet. Before M1, each enabled candidate must have an official source URL, source type, exact claim, `checked_at`, recheck/expiry date, confidence, privacy/data class, quota scope/reset, and a verified no-auto-charge control. Missing or stale evidence maps to `UNKNOWN` or `PAUSED`, and neither state enters a `free-*` alias.

## Admission rules

1. Model listing is discovery only. It does not establish that a model is free.
2. A `free-*` alias accepts only an eligible `PERMANENT_FREE` or `FREE_ALLOWANCE` deployment whose evidence is fresh and whose billing guard is satisfied.
3. `TRIAL`, `PROMOTION`, `EVAL_ONLY`, `PAID`, `PAUSED`, `RETIRED`, and `UNKNOWN` never enter `free-*`.
4. Provider-defined project/account quotas are stored at that scope. Extra API keys do not multiply the quota.
5. If price, quota scope, or post-limit behavior is unknown, fail closed and do not invoke the deployment.

Official URLs and evidence claims remain to be attached during provider verification. M0 intentionally uses only the supplied baseline and local reference repositories; it did not browse or probe provider services.
