# Native Responses contract smoke test — 2026-10-04

This is a sanitized live smoke test made before implementing the local Responses proxy. The only prompt content was synthetic (“reply with a short greeting” and a synthetic `greet` function). Credentials, response IDs, account identifiers, generated text, and raw provider bodies are not retained. See `tests/fixtures/live_contracts/` for shape-only evidence.

## Results

| Provider | Endpoint/model | Non-stream | SSE stream | Function call |
|---|---|---|---|---|
| Groq | `/openai/v1/responses`, `openai/gpt-oss-20b` | HTTP 200, completed response with message/output_text | HTTP 200, `text/event-stream`, response lifecycle and text delta events | HTTP 200, completed `function_call` named `greet` |
| OpenRouter | `/api/v1/responses`, `openrouter/free` | HTTP 200, completed response with message/output_text | HTTP 200, `text/event-stream`, response lifecycle and text delta events | HTTP 200, completed `function_call` named `greet` |

OpenRouter `GET /api/v1/key` returned HTTP 200 and `data.is_free_tier=true`. Only that boolean was retained. Its runtime `/responses` model selection varied between requests, so the generic alias remains explicitly public-only. One early probe with a small `max_output_tokens` returned `incomplete` with only reasoning output; the successful conformance probes used a larger budget and checked for actual message or function-call output rather than treating HTTP 200 as success.

Both endpoints use the OpenResponses envelope needed by the proxy for the tested paths. The fixtures deliberately omit IDs and response content. Groq documents its Responses endpoint as beta and lists unsupported stateful fields; PoolRouter therefore sends `store:false` and does not expose `previous_response_id`, background, reusable prompt, or other unverified stateful features in M1A.

## Sources

- [Groq Responses API](https://console.groq.com/docs/responses-api)
- [Groq model card: GPT-OSS 20B](https://console.groq.com/docs/model/openai/gpt-oss-20b)
- [Groq Free Plan rate limits](https://console.groq.com/docs/rate-limits)
- [OpenRouter Responses API](https://openrouter.ai/docs/api/api-reference/responses/create-responses)
- [OpenRouter API key status](https://openrouter.ai/docs/api/api-reference/keys/get-current-key)
