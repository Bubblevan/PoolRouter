# ADR 0004: Pin LiteLLM community dependency

Status: Accepted for M0.5  
Date: 2026-10-04

## Decision

Pin the Python dependency to `litellm==1.103.2`. The official GitHub Releases page marked `v1.103.2` Latest stable on the review date; its release commit is `f69b2103dfc0f7a41f65555fd66df05274584e5a`. PyPI published version 1.103.2 on 2026-10-01 and declares MIT. The supplied candidate `v1.103.0` was superseded, so M0.5 selected the current stable patch. No prerelease, `latest`, or `main` reference is used.

The pin is a Python package dependency in `pyproject.toml`. Docker mode is not selected, so no Docker tag, digest, or signature is part of this decision. The local reference checkout remains read-only and did not contain the selected newer tag at audit time; its existing v1.103.0 tag remains untouched.

## License boundary and capability use

| Capability | Source path | License | Needed by PoolRouter? | Replacement if enterprise-only |
|---|---|---|---|---|
| Provider compatibility and request translation | Core `litellm` SDK, `litellm/llms/` | MIT according to the selected PyPI artifact; repository root license applies MIT outside `enterprise/` | Yes | Keep supported community provider integrations; otherwise a narrowly scoped direct OpenAI-compatible adapter after separate review. |
| Router, retry and cooldown primitives | Core `litellm/router.py`, `litellm/router_utils/` | MIT outside `enterprise/` | Candidate for M1 after behavior review | PoolRouter admission stays outside LiteLLM; implement local retry policy only for a concrete gap. |
| HTTP proxy server, Responses, and streaming routes | LiteLLM `proxy` extra | Extra declares `litellm-enterprise==0.1.69.post1` plus proxy dependencies; not selected | No | Build a small PoolRouter-owned local HTTP API on FastAPI and call the core LiteLLM SDK. Keep Responses/streaming compatibility in PoolRouter's own adapters. |
| Enterprise proxy features | `enterprise/` and `litellm-enterprise` distribution | Separate enterprise license/package boundary | No | PoolRouter-owned API layer, evidence/admission, local policy and SQLite state. |
| Spend tracking/database integrations | Community and enterprise paths vary by feature | Review exact source path before use | Not assumed | PoolRouter-owned quota/evidence ledger and local SQLite. |

The v1.103.2 upstream root license places any `enterprise/` content under a separate license and content outside it under MIT. PyPI marks the selected artifact MIT. Its `proxy` extra declares `litellm-enterprise==0.1.69.post1`, so PoolRouter deliberately installs only the core SDK and will not select that extra, copy enterprise source, or depend on the separate enterprise distribution. LiteLLM remains an upstream dependency; PoolRouter owns its HTTP API, evidence, admission, lifecycle, privacy, quota scope, and zero-cost invariant.

## Relevant release review

The v1.103.2 release is a stable patch release whose published notes describe backports and fixes (including proxy and provider fixes); the notes do not identify a breaking change relevant to the planned PoolRouter boundary. This is not a substitute for M1 contract tests before relying on endpoint, streaming, or tool-call details.

## Upgrade policy

Keep this exact pin until a deliberate dependency review. For each proposed update, verify the official stable release and PyPI artifact/version, inspect release notes for the proxy, Responses, provider, retry, and streaming paths PoolRouter actually uses, review the license boundary, update the pin, and run PoolRouter tests. Do not float to `latest`, `main`, or a development version.

## Sources

- [LiteLLM v1.103.2 release](https://github.com/BerriAI/litellm/releases/tag/v1.103.2)
- [LiteLLM 1.103.2 on PyPI](https://pypi.org/project/litellm/1.103.2/)
- [Selected release root license](https://raw.githubusercontent.com/BerriAI/litellm/v1.103.2/LICENSE)
- Local read-only audit: the reference checkout root `litellm/LICENSE`; no enterprise files were copied.
