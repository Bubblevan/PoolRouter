# Manual provider smoke test — 2026-10-04

This records one-off authenticated API smoke tests made at the user's request. Requests used only the public text `Hello!`; no provider key or account ID is recorded here. The examples use environment variables, not literal credentials. These calls were made directly to provider APIs; PoolRouter's runtime router is not implemented by this test.

## Environment variables

The local `.env` used these names:

| Provider | Credential | Account/billing assertion |
|---|---|---|
| Groq | `GROQ_API_KEY` | `GROQ_ACCOUNT_TIER=free` |
| OpenRouter | `OPENROUTER_API_KEY` | No separate plan assertion used for the free models below. |
| Cloudflare Workers AI | `CLOUDFLARE_API_TOKEN` | `CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_WORKERS_PLAN=free` |

Account plan values are user assertions, not provider-verified facts. Never commit `.env` or paste credential values into logs, documentation, or issue reports.

## 1. Groq — OpenAI-compatible chat completions

Endpoint: `POST https://api.groq.com/openai/v1/chat/completions`  
Model: `openai/gpt-oss-20b`  
Result: HTTP 200; response: `Hello! How can I help you today?`

The first short-output attempt returned an empty content field. A retry with `max_tokens: 64` returned the text above. The test was made under the configured Free-tier assertion. Groq rate limits are organization-scoped; API keys in one organization do not multiply quota. The Developer plan has model prices and is pay-as-you-go, so do not treat this model as universally $0 outside a verified Free account.

```powershell
curl.exe https://api.groq.com/openai/v1/chat/completions `
  -H "Authorization: Bearer $env:GROQ_API_KEY" `
  -H "Content-Type: application/json" `
  --data-raw '{"model":"openai/gpt-oss-20b","messages":[{"role":"user","content":"Hello!"}],"max_tokens":64}'
```

Sources: [Groq API reference](https://console.groq.com/docs/api-reference), [Groq rate limits](https://console.groq.com/docs/rate-limits), [Groq billing FAQs](https://console.groq.com/docs/billing-faqs).

## 2. OpenRouter — automatic free routing and a concrete free model

### Automatic router

Model: `openrouter/free`  
Result: HTTP 200; response: `Hello! 👋 How can I assist you with anything today?`

This alias chooses an available free model automatically. It is appropriate for public test text; do not use it for private or sensitive prompts because the selected upstream may vary and free-plan policy routing is limited.

```powershell
curl.exe https://openrouter.ai/api/v1/chat/completions `
  -H "Authorization: Bearer $env:OPENROUTER_API_KEY" `
  -H "Content-Type: application/json" `
  --data-raw '{"model":"openrouter/free","messages":[{"role":"user","content":"Hello!"}]}'
```

### Concrete model

Model: `liquid/lfm-2.5-2.6b:free`  
Result: HTTP 200; response: `Hey there! How can I help you today?`

Before calling it, the live OpenRouter model catalog showed zero prompt and completion prices for this concrete text model. Recheck model presence, modalities, and both prices at runtime; catalog data is dynamic. The requested `meta-llama/llama-3.2-3b-instruct:free` was not present in the current free catalog and its model-detail request returned 404, so it was not called. Another free-model endpoint returned 429 during testing; the response body was not retained, so the specific cause is unknown.

```powershell
curl.exe https://openrouter.ai/api/v1/chat/completions `
  -H "Authorization: Bearer $env:OPENROUTER_API_KEY" `
  -H "Content-Type: application/json" `
  --data-raw '{"model":"liquid/lfm-2.5-2.6b:free","messages":[{"role":"user","content":"Hello!"}],"max_tokens":96,"provider":{"allow_fallbacks":false}}'
```

Sources: [OpenRouter quickstart and model-list API](https://openrouter.ai/docs/quickstart), [single-model detail API](https://openrouter.ai/docs/api/api-reference/models/get-model), [Free plan and limits](https://openrouter.ai/pricing/).

## 3. Cloudflare Workers AI — OpenAI-compatible chat completions

Endpoint: `POST https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/v1/chat/completions`  
Model: `@cf/meta/llama-3.2-1b-instruct`  
Result: HTTP 200; response: `Hello! How can I assist you today?`

The model was confirmed in the account's model catalog. Several earlier catalog-listed Free candidates returned HTTP 200 but an empty content field; testing stopped at the first non-empty response. The originally requested `@cf/meta/llama-3.1-8b-instruct` returned HTTP 410. The account catalog surfaced `@cf/meta/llama-3.1-8b-instruct-fp8` instead; no substitute request was made for that model.

```powershell
curl.exe "https://api.cloudflare.com/client/v4/accounts/$env:CLOUDFLARE_ACCOUNT_ID/ai/v1/chat/completions" `
  -H "Authorization: Bearer $env:CLOUDFLARE_API_TOKEN" `
  -H "Content-Type: application/json" `
  --data-raw '{"model":"@cf/meta/llama-3.2-1b-instruct","messages":[{"role":"user","content":"Hello!"}]}'
```

The Workers Free plan includes 10,000 Neurons per day, resetting at 00:00 UTC. On Free, exceeding an allowance fails; on Workers Paid, usage above the included allocation is billable. These tests used the `CLOUDFLARE_WORKERS_PLAN=free` user assertion and were short manual requests. A future PoolRouter runtime still needs the local Neuron accounting guard before admitting Cloudflare.

Sources: [Cloudflare OpenAI-compatible endpoints](https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/), [Workers AI model catalog](https://developers.cloudflare.com/workers-ai/models/), [pricing and Neuron limits](https://developers.cloudflare.com/workers-ai/platform/pricing/).

## Summary

| Provider | Method | Model | Result |
|---|---|---|---|
| Groq | OpenAI-compatible `/chat/completions` | `openai/gpt-oss-20b` | HTTP 200, non-empty response after increasing output limit. |
| OpenRouter | `/api/v1/chat/completions`, automatic alias | `openrouter/free` | HTTP 200, non-empty response. |
| OpenRouter | `/api/v1/chat/completions`, concrete free model | `liquid/lfm-2.5-2.6b:free` | HTTP 200, non-empty response after confirming current zero input/output price. |
| Cloudflare Workers AI | OpenAI-compatible `/ai/v1/chat/completions` | `@cf/meta/llama-3.2-1b-instruct` | HTTP 200, non-empty response. |

These are dated smoke-test observations, not a durable model allowlist or proof that a future request is free. Revalidate pricing, model availability, account plan, quota, and privacy policy before each runtime admission.
