# M1A local gateway — Groq and OpenRouter

PoolRouter exposes a local OpenAI-style gateway at `http://127.0.0.1:4000`. M1A routes only to Groq Free Plan allowance and OpenRouter Free models. Cloudflare is deliberately not an M1A runtime provider; its paid-overage risk still requires a Neuron guard.

## Configure and run

Copy the variable names from `.env.example` into the ignored local `.env` and supply provider credentials. Set `GROQ_ACCOUNT_TIER=free` only while the Groq account remains on Free; it is an operator assertion. PoolRouter verifies OpenRouter's key state online and fails closed unless `is_free_tier` is exactly `true`. The local `POOLROUTER_API_KEY` is required for all `/v1/*` routes. The sample `.env.example` contains no credentials.

```powershell
uv sync --all-extras --locked
uv run python -m poolrouter
```

The server binds only to `127.0.0.1:4000`. `/healthz` is unauthenticated. All `/v1/*` endpoints require `Authorization: Bearer $env:POOLROUTER_API_KEY` and an explicit `X-PoolRouter-Data-Class: public` header on inference requests. Omitting or changing the class fails closed. M1A has no private/sensitive data route.

## Model aliases

| Alias | Deployment order | Scope |
|---|---|---|
| `free-public` | Groq `openai/gpt-oss-20b`, then OpenRouter `openrouter/free` | Explicitly public prompts; OpenRouter's selected upstream can vary. |
| `groq-free` | Groq `openai/gpt-oss-20b` | Explicitly public prompts; requires `GROQ_ACCOUNT_TIER=free` and current official model evidence. |
| `openrouter-free` | OpenRouter `openrouter/free` | Explicitly public prompts and runtime `is_free_tier=true`. |

`GET /v1/models` lists only these aliases. It does not expose provider credentials or imply that a provider is currently eligible; each inference request rechecks account/model admission. The catalog adapter can project concrete OpenRouter entries only when both prompt and completion prices are zero and modality is text-to-text. M1A's stable public alias does not pin one of those dynamic models.

## Compatibility and safety

- `POST /v1/chat/completions` is forwarded through LiteLLM Core SDK (`litellm==1.103.2`), with SDK retries disabled. PoolRouter controls deployment fallback.
- `POST /v1/responses` is sent to native provider Responses endpoints over HTTPX. `store:false` is forced. Stateful fields that Groq does not support (`previous_response_id`, `background`, reusable `prompt`, `prompt_cache_key`, `safety_identifier`, `include`, and `truncation`) are rejected.
- Reasoning-only/empty HTTP 200 responses are `DEGRADED_RESPONSE`; they can fall back before output. Reasoning content is stripped from Responses bodies and streams.
- Fallback is limited to rate limit, quota, capacity, timeout, upstream 5xx, and degraded responses. Authentication, malformed request/tool schema, unsupported capability, and policy errors do not fallback. Once streamed output is sent, a later failure returns an error event and never restarts on another provider.
- OpenRouter attempts are capped at 50 in a rolling 24-hour process-local window; every attempted request counts. Groq selected rate-limit headers are read from LiteLLM response metadata when present. Provider quotas remain authoritative.
- Failure responses use a normalized provider/model/status/code/category/retryability/retry-after/safe-message structure. Exhaustion returns HTTP 503 with `FREE_POOL_EXHAUSTED`. Success responses include `X-PoolRouter-Provider`, `X-PoolRouter-Model`, `X-PoolRouter-Fallback-Attempts`, and `X-PoolRouter-Lifecycle`.
- No prompt/response logging, credential logging, paid fallback, private route, Cloudflare route, consumer alias, proxy extra, or enterprise LiteLLM feature is included.

## Offline verification

```powershell
uv run pytest -p no:cacheprovider
```

The suite uses fake transports and synthetic payloads. CI runs the same suite offline under Python 3.12 and does not need provider secrets.

## Local live smoke requests

Use only synthetic public prompts. Examples below do not print or put provider keys in command history:

```powershell
$headers = @{ Authorization = "Bearer $env:POOLROUTER_API_KEY"; "X-PoolRouter-Data-Class" = "public" }
Invoke-RestMethod http://127.0.0.1:4000/v1/chat/completions -Method Post -Headers $headers -ContentType application/json -Body '{"model":"groq-free","messages":[{"role":"user","content":"Say hi briefly."}],"max_tokens":64}'
Invoke-RestMethod http://127.0.0.1:4000/v1/responses -Method Post -Headers $headers -ContentType application/json -Body '{"model":"openrouter-free","input":"Say hi briefly.","max_output_tokens":256}'
```

For a full live provider matrix, run `scripts/live_smoke.py`; it uses credentials from local `.env`, displays only provider/status/semantic result, and uses only synthetic prompts. The live matrix and forced Groq 429 fallback result are recorded in `docs/evidence/live-gateway-smoke-2026-10-04.md`. The forced 429 was injected locally before any Groq network request.
