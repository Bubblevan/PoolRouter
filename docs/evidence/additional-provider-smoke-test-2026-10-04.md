# Additional provider smoke tests — 2026-10-04

Manual live checks requested by the repository owner. Calls used only the synthetic prompt `Reply with exactly: hi`. Credentials were loaded from the local `.env`; no key, account identifier, response body, or provider error body was stored in this report. These were direct provider API checks, not PoolRouter runtime routes.

## Provider credentials found in `.env`

The variable names present at the time of inspection were `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `CLOUDFLARE_API_TOKEN`, `GLM_API_KEY`, `SILICONFLOW_API_KEY`, `CEREBRAS_API_KEY`, `MODELSCOPE_ACCESS_TOKEN`, `GEMINI_API`, `NVIDIA_API_KEY`, and `OPENCODE_ZEN_API_KEY`. The file also contains PoolRouter and account/plan configuration variables; their values are not recorded here.

## Results

| Provider | Credential variable | Model / operation | Result |
|---|---|---|---|
| BigModel | `GLM_API_KEY` | `glm-4.7-flash`, `POST /api/paas/v4/chat/completions` | HTTP 429; no semantic reply. The provider rejected the request as rate limited. |
| Cerebras | `CEREBRAS_API_KEY` | Authenticated `GET /v1/models` only | HTTP 200; catalog includes `qwen-3.8-27b` and `gpt-oss-120b`. No inference call was made. Current official pricing lists Qwen 3.8 27B at `$0.99/M` input and `$1.49/M` output; the Developer tier is self-serve pay-as-you-go with a one-time promotional credit, not a zero-priced model/tier. |
| ModelScope | `MODELSCOPE_ACCESS_TOKEN` | `Qwen/Qwen3.5-35B-A3B`, `POST /v1/chat/completions` | HTTP 200; non-empty assistant reply. |
| OpenCode Zen | `OPENCODE_ZEN_API_KEY` | `mimo-v2.6-flash-free` and `longcat-2.5-preview-free`, `POST /zen/v1/chat/completions` | Both models were listed as free in the live model directory; both inference requests returned HTTP 403, no semantic reply. |
| SiliconFlow | `SILICONFLOW_API_KEY` | `XingChenAGI/Xing4.0-29B`, `POST /v1/chat/completions` | Current pricing lists input/output as free and the model was present in the account catalog. Initial requests timed out or returned HTTP 200 with empty text at `max_tokens: 32`; increasing to 128 produced a non-empty response (HTTP 200, `finish_reason=stop`). |
| Gemini Developer API | `GEMINI_API` | `gemini-3.8-flash`, `gemini-2.5-flash`, `gemini-3.5-flash`, `generateContent` | Model directory returned HTTP 200. Inference returned 403, 404, and 403 respectively; no semantic reply. |
| NVIDIA NIM | `NVIDIA_API_KEY` | `nvidia/nemotron-3.5-lightning-30b-a3b`, `POST /v1/chat/completions` | The current Build catalog marks it a free downloadable endpoint; HTTP 200 with a non-empty assistant reply. |

For BigModel, the request used a small `max_tokens` limit and did not enable thinking. The 429 means availability was not verified; this report does not infer whether the cause was account quota, rate limits, or another provider-side condition.

For ModelScope, the authenticated model directory returned HTTP 200 and contained both example IDs `Qwen/Qwen3.5-35B-A3B` and `Qwen/Qwen3.5-27B`; the first example ID was selected for the call. This verifies one current Chat Completions path only; it does not establish a durable free quota or verify the separate Responses API example.

For OpenCode Zen, `GET /zen/v1/models` returned HTTP 200 and listed the selected zero-price models. Two free models returned HTTP 403. No response body was retained, so the exact cause is unknown; this looks like an access/policy issue for the credential or account, rather than an individual model ID. OpenCode describes its free model set as time-limited, and states that some free-model prompts may be collected to improve models. Keep requests synthetic/public.

For SiliconFlow, the live official pricing page listed `XingChenAGI/Xing4.0-29B` at zero input and output price, and the authenticated `/v1/models` catalog included it. A 32-token output cap yielded an empty response; with 128 tokens the model returned non-empty text and included reasoning content. Only response shape and content length were kept, not response text.

For Gemini, the official pricing page advertises a free tier for selected models. The live authenticated directory included `gemini-3.8-flash`, `gemini-2.5-flash`, and `gemini-3.5-flash`. Their inference status codes were 403, 404, and 403. No response bodies were retained, so the exact account/model cause is unknown. The directory response does not prove that the key's project is entitled to free inference.

For NVIDIA, the current Build page describes free serverless API access for development and lists `nemotron-3.5-lightning-30b-a3b` as a downloadable free endpoint. The direct API call returned HTTP 200 with a semantic response. NVIDIA's trial page states that inputs and outputs may be logged and used to improve services; keep traffic synthetic/public.

## Sanitized request shapes

```text
POST https://open.bigmodel.cn/api/paas/v4/chat/completions
model=glm-4.7-flash
max_tokens=64
result=429

GET https://api.cerebras.ai/v1/models
result=200; models include qwen-3.8-27b and gpt-oss-120b
inference=not sent (current published model prices are nonzero)

GET https://api-inference.modelscope.cn/v1/models
result=200; requested Qwen/Qwen3.5 IDs present
POST https://api-inference.modelscope.cn/v1/chat/completions
model=Qwen/Qwen3.5-35B-A3B; result=200; non-empty reply

GET https://api.siliconflow.cn/v1/models
result=200; XingChenAGI/Xing4.0-29B listed at zero input/output price
POST https://api.siliconflow.cn/v1/chat/completions
model=XingChenAGI/Xing4.0-29B; max_tokens=128; result=200; non-empty reply

GET https://generativelanguage.googleapis.com/v1beta/models
result=200; selected generateContent model IDs listed
POST .../gemini-3.8-flash:generateContent; result=403
POST .../gemini-2.5-flash:generateContent; result=404
POST .../gemini-3.5-flash:generateContent; result=403

GET https://integrate.api.nvidia.com/v1/models
result=200; selected Nemotron model listed
POST https://integrate.api.nvidia.com/v1/chat/completions
model=nvidia/nemotron-3.5-lightning-30b-a3b; result=200; non-empty reply

GET https://opencode.ai/zen/v1/models
result=200; selected free model present
POST https://opencode.ai/zen/v1/chat/completions
models=mimo-v2.6-flash-free, longcat-2.5-preview-free; both result=403
```

## Official references checked

- [BigModel GLM-4.7-Flash documentation](https://docs.bigmodel.cn/cn/guide/models/free/glm-4.7-flash) — model ID and chat-completions endpoint.
- [Cerebras Inference pricing](https://www.cerebras.ai/pricing) — Developer tier pricing, models, and promotional-credit terms.
- [ModelScope API-Inference documentation](https://www.modelscope.cn/docs/model-service/API-Inference/intro) — user-provided API-Inference documentation entry point.
- [OpenCode Zen documentation](https://opencode.ai/docs/zen/) — API endpoints, current free-model catalog/prices, limited-time status, and privacy notes.
- [SiliconFlow model pricing](https://siliconflow.cn/pricing) — current zero-price and priced model rows.
- [Google Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) — free-tier model pricing and data-use distinction.
- [NVIDIA Build model catalog](https://build.nvidia.com/nvidia/nemotron-3.5-lightning-30b-a3b) — free endpoint and trial data-handling notice.

## Summary

| Provider | Outcome |
|---|---|
| BigModel | Not verified: provider returned HTTP 429. |
| Cerebras | No free inference attempted: current listed model is paid; only the read-only catalog was queried. |
| ModelScope | Verified: one non-streaming Chat Completions request returned a semantic reply. |
| OpenCode Zen | Not verified: two current free models listed; both inference calls returned HTTP 403. |
| SiliconFlow | Verified: one zero-price model returned a semantic reply after increasing the output cap. |
| Gemini Developer API | Not verified: live model listing worked; current candidates returned 403/404. |
| NVIDIA NIM | Verified: one current free development endpoint returned a semantic reply. |

These are dated observations, not permanent availability or billing guarantees. Recheck the provider's current model list, terms, price, account eligibility, and quota before routing future traffic.
