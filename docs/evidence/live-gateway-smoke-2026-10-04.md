# Local gateway live smoke matrix — 2026-10-04

Live checks used only synthetic public prompts and the user's local credentials. This report retains no prompts, generated text, auth headers, response IDs, or account metadata. Each request was sent through PoolRouter bound to `127.0.0.1:4000`.

| Provider alias | Chat | Chat stream | Chat function call | Responses | Responses stream | Responses function call |
|---|---|---|---|---|---|---|
| `groq-free` | INTERMITTENT | PASS | PASS | PASS | PASS | PASS |
| `openrouter-free` | INTERMITTENT | PASS | PASS | PASS | PASS | PASS |

Each PASS means HTTP 200 plus the expected semantic output (non-empty assistant content, a streamed content delta, or a `greet` function call). In the final run, Groq and OpenRouter non-stream Chat each returned both 200 and 503 across repeated short synthetic requests; Groq's immediate retry succeeded, while OpenRouter's responses varied across runs. A direct LiteLLM call through the final custom HTTPX client returned non-empty Chat content for both providers. Treat the non-stream dynamic free aliases as intermittently available; their failed replies are classified as degraded/exhausted rather than relayed as success. OpenRouter admission re-read the key-status endpoint and observed `is_free_tier=true`; no other key metadata was retained.

A separate Groq Chat probe confirmed the official response includes rate-limit headers. The final LiteLLM custom HTTPX client hook observed both remaining-request and remaining-token dimensions; only those two values enter the process-local quota ledger.

## Fallback and stream commitment

- A local test gateway injected a synthetic Groq 429 before any Groq network call, then routed the same public Chat request to OpenRouter. The response was HTTP 200 with `X-PoolRouter-Provider: openrouter` and `X-PoolRouter-Fallback-Attempts: 1`.
- Offline regression tests confirm a Responses stream can fallback when no semantic output was emitted yet, and that a disconnect after the first output event produces an error event without contacting OpenRouter again.

The final credential-free suite has 34 passing tests. CI uses synthetic/mock transports only and requires no secrets.
