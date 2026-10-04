from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import Body, Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from poolrouter.config import Settings
from poolrouter.providers.openrouter import OpenRouterProvider
from poolrouter.api.auth import auth_dependency
from poolrouter.api.errors import error_response
from poolrouter.runtime.admission import Admission
from poolrouter.runtime.attempts import may_fallback
from poolrouter.runtime.errors import ProviderFailure, normalize_failure
from poolrouter.runtime.health import Health
from poolrouter.runtime.models import ALIASES, Deployment
from poolrouter.runtime.quota import QuotaLedger
from poolrouter.transports.chat_litellm import chat_completion, close_chat_http_client, response_quota_headers
from poolrouter.transports.responses_native import post_response, semantic_response_ok, strip_reasoning


def create_app(settings: Settings | None = None, *, client: httpx.AsyncClient | None = None,
               chat_call=chat_completion) -> FastAPI:
    config = settings or Settings.from_env()
    client = client or httpx.AsyncClient(timeout=90)
    openrouter = OpenRouterProvider(config, client)
    admission = Admission(config, openrouter)
    quota = QuotaLedger()
    health = Health()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        try:
            yield
        finally:
            await close_chat_http_client()
            await client.aclose()

    app = FastAPI(title="PoolRouter", version="0.1.0", lifespan=lifespan)
    app.state.settings = config
    app.state.http_client = client
    app.state.quota = quota
    app.state.health = health

    auth = auth_dependency(config.local_api_key)

    def data_class(header: str | None) -> str:
        if header != "public":
            raise ProviderFailure("poolrouter", "", 403, "public_class_required", "POLICY", False, None,
                                  "Free public aliases accept only requests explicitly classified as public.")
        return header

    def response_headers(target: Deployment, attempts: int) -> dict[str, str]:
        return {"X-PoolRouter-Provider": target.provider,
                "X-PoolRouter-Model": target.model,
                "X-PoolRouter-Fallback-Attempts": str(max(0, attempts - 1)),
                "X-PoolRouter-Lifecycle": "FREE_ALLOWANCE"}

    def candidates_or_error(alias: str, classification: str) -> list[Deployment]:
        if alias not in ALIASES:
            raise ProviderFailure("poolrouter", alias, 400, "unknown_model_alias", "BAD_REQUEST", False, None,
                                  "Use one of the advertised PoolRouter free aliases.")
        if classification != "public":
            raise ProviderFailure("poolrouter", alias, 403, "public_class_required", "POLICY", False, None,
                                  "Free public aliases accept only requests explicitly classified as public.")
        return []

    async def available(alias: str, classification: str) -> list[Deployment]:
        candidates_or_error(alias, classification)
        return [target for target in await admission.candidates(alias, classification)
                if target.provider not in health.quarantined and quota.can_attempt(target.provider)]

    def failure_from_http(target: Deployment, response: httpx.Response) -> ProviderFailure:
        try:
            error = response.json().get("error", {})
        except (ValueError, AttributeError):
            error = {}
        return normalize_failure(target.provider, target.model, response.status_code,
                                 str(error.get("code") or "") or None,
                                 str(error.get("message") or "Upstream request failed"),
                                 response.headers.get("retry-after"))

    def failure_from_exception(target: Deployment, exc: Exception) -> ProviderFailure:
        status = getattr(exc, "status_code", None)
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", status)
        code = getattr(exc, "code", None)
        return normalize_failure(target.provider, target.model, status, str(code) if code else None,
                                 str(exc))

    def chat_semantic_ok(value: dict) -> bool:
        choices = value.get("choices", [])
        return any((choice.get("message", {}).get("content")
                    or choice.get("message", {}).get("tool_calls")) for choice in choices)

    def to_dict(value: Any) -> dict:
        if isinstance(value, dict):
            return value
        if hasattr(value, "model_dump"):
            return value.model_dump(exclude_none=True)
        if hasattr(value, "dict"):
            return value.dict(exclude_none=True)
        return dict(value)

    def strip_chat_reasoning(value: dict) -> dict:
        def scrub(part):
            if isinstance(part, dict):
                for key in list(part):
                    if key.lower() in {"reasoning", "reasoning_content", "reasoning_details"}:
                        part.pop(key, None)
                    else:
                        scrub(part[key])
            elif isinstance(part, list):
                for item in part:
                    scrub(item)
        for choice in value.get("choices", []):
            scrub(choice)
        return value

    def observe_chat_headers(target: Deployment, result: Any) -> None:
        if target.provider != "groq":
            return
        hidden = getattr(result, "_hidden_params", {}) or {}
        headers = hidden.get("headers", {}) if isinstance(hidden, dict) else {}
        selected = {str(k).lower(): str(v) for k, v in dict(headers or {}).items()}
        selected.update(response_quota_headers())
        quota.observe_groq_headers(selected)

    def stream_has_output(chunk: dict) -> bool:
        for choice in chunk.get("choices", []):
            delta = choice.get("delta", {})
            if delta.get("content") or delta.get("tool_calls") or delta.get("function_call"):
                return True
        return False

    def chunk_frame(chunk: dict, alias: str) -> bytes:
        scrubbed = strip_chat_reasoning(chunk)
        scrubbed["model"] = alias
        return ("data: " + json.dumps(scrubbed, ensure_ascii=False, separators=(",", ":")) + "\n\n").encode()

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok", "ready_providers": {
            "groq": "groq" not in health.quarantined,
            "openrouter": "openrouter" not in health.quarantined,
        }}

    @app.get("/v1/models", dependencies=[Depends(auth)])
    async def models():
        return {"object": "list", "data": [{"id": name, "object": "model", "owned_by": "poolrouter"}
                                             for name in ALIASES]}

    @app.post("/v1/chat/completions", dependencies=[Depends(auth)])
    async def chat_completions(request: Request, payload: dict = Body(...),
                               classification: str | None = Header(default=None, alias="X-PoolRouter-Data-Class")):
        alias = str(payload.get("model", ""))
        try:
            pool = await available(alias, data_class(classification))
        except ProviderFailure as failure:
            return error_response(failure)
        if not isinstance(payload.get("messages"), list) or not payload["messages"]:
            return error_response(normalize_failure("poolrouter", alias, 400, "invalid_messages",
                                                "messages must be a non-empty array"))
        if payload.get("stream"):
            return await chat_stream(alias, payload, pool)
        failures: list[ProviderFailure] = []
        for number, target in enumerate(pool, start=1):
            quota.record_attempt(target.provider)
            try:
                result = await chat_call(config, target, payload)
                value = strip_chat_reasoning(to_dict(result))
                observe_chat_headers(target, result)
                if not chat_semantic_ok(value):
                    failure = normalize_failure(target.provider, target.model, 200, "empty_completion",
                                                "Provider returned no assistant text or tool call")
                    failure.category = "DEGRADED_RESPONSE"
                    failure.retryable = True
                    health.record(target.provider, False)
                else:
                    health.record(target.provider, True)
                    value["model"] = alias
                    return JSONResponse(value, headers=response_headers(target, number))
            except Exception as exc:
                failure = failure_from_exception(target, exc)
                health.record(target.provider, False)
            failures.append(failure)
            if not may_fallback(failure):
                return error_response(failure)
        return error_response(failures[-1] if failures else normalize_failure(
            "poolrouter", alias, 503, "no_eligible_deployment", "No eligible free provider"), exhausted=True)

    async def chat_stream(alias: str, payload: dict, pool: list[Deployment]):
        failures: list[ProviderFailure] = []
        for number, target in enumerate(pool, start=1):
            quota.record_attempt(target.provider)
            iterator = None
            try:
                result = await chat_call(config, target, {**payload, "stream": True})
                observe_chat_headers(target, result)
                iterator = result.__aiter__()
                buffered = []
                first = None
                while True:
                    chunk = to_dict(await iterator.__anext__())
                    if stream_has_output(chunk):
                        first = chunk
                        break
                    buffered.append(chunk)
            except StopAsyncIteration:
                failure = normalize_failure(target.provider, target.model, 200, "empty_stream",
                                            "Provider completed without assistant output")
                failure.category = "DEGRADED_RESPONSE"
                failure.retryable = True
                health.record(target.provider, False)
            except Exception as exc:
                failure = failure_from_exception(target, exc)
                health.record(target.provider, False)
            else:
                health.record(target.provider, True)
                async def chunks():
                    try:
                        for item in buffered:
                            yield chunk_frame(item, alias)
                        yield chunk_frame(first, alias)
                        async for item in iterator:
                            yield chunk_frame(to_dict(item), alias)
                    except Exception as exc:
                        failure = failure_from_exception(target, exc)
                        health.record(target.provider, False)
                        yield ("data: " + json.dumps({"error": failure.as_dict()}, separators=(",", ":")) + "\n\n").encode()
                    finally:
                        yield b"data: [DONE]\n\n"
                return StreamingResponse(chunks(), media_type="text/event-stream",
                                         headers=response_headers(target, number))
            failures.append(failure)
            if not may_fallback(failure):
                return error_response(failure)
        return error_response(failures[-1] if failures else normalize_failure(
            "poolrouter", alias, 503, "no_eligible_deployment", "No eligible free provider"), exhausted=True)

    @app.post("/v1/responses", dependencies=[Depends(auth)])
    async def responses(request: Request, payload: dict = Body(...),
                        classification: str | None = Header(default=None, alias="X-PoolRouter-Data-Class")):
        alias = str(payload.get("model", ""))
        try:
            pool = await available(alias, data_class(classification))
        except ProviderFailure as failure:
            return error_response(failure)
        unsupported = {"previous_response_id", "background", "prompt", "prompt_cache_key",
                       "safety_identifier", "include", "truncation"}.intersection(payload)
        if unsupported:
            return error_response(normalize_failure("poolrouter", alias, 400, "unsupported_responses_feature",
                                                "This Responses feature is not supported by the M1A provider contract."))
        if "input" not in payload:
            return error_response(normalize_failure("poolrouter", alias, 400, "missing_input", "input is required"))
        if payload.get("stream"):
            return await responses_stream(alias, payload, pool)
        failures: list[ProviderFailure] = []
        for number, target in enumerate(pool, start=1):
            quota.record_attempt(target.provider)
            try:
                result = await post_response(client, config, target, payload)
                if result.status_code >= 400:
                    failure = failure_from_http(target, result)
                    health.record(target.provider, False)
                else:
                    body = result.json()
                    if not semantic_response_ok(body):
                        failure = normalize_failure(target.provider, target.model, 200, "empty_response",
                                                    "Provider returned no assistant text or function call")
                        failure.category = "DEGRADED_RESPONSE"
                        failure.retryable = True
                        health.record(target.provider, False)
                    else:
                        health.record(target.provider, True)
                        safe = strip_reasoning(body)
                        safe["model"] = alias
                        return JSONResponse(safe, headers=response_headers(target, number))
            except (httpx.HTTPError, ValueError) as exc:
                failure = normalize_failure(target.provider, target.model, None, "transport_error", type(exc).__name__)
                health.record(target.provider, False)
            failures.append(failure)
            if not may_fallback(failure):
                return error_response(failure)
        return error_response(failures[-1] if failures else normalize_failure(
            "poolrouter", alias, 503, "no_eligible_deployment", "No eligible free provider"), exhausted=True)

    async def responses_stream(alias: str, payload: dict, pool: list[Deployment]):
        failures: list[ProviderFailure] = []
        for number, target in enumerate(pool, start=1):
            quota.record_attempt(target.provider)
            try:
                body = {**payload, "model": target.model, "stream": True, "store": False}
                headers = {"Authorization": f"Bearer {config.groq_api_key if target.provider == 'groq' else config.openrouter_api_key}",
                           "Content-Type": "application/json"}
                req = client.build_request("POST", f"{target.base_url}/responses", headers=headers, json=body)
                upstream = await client.send(req, stream=True)
                if upstream.status_code >= 400:
                    raw = await upstream.aread()
                    try:
                        err = json.loads(raw).get("error", {})
                    except (json.JSONDecodeError, AttributeError):
                        err = {}
                    failure = normalize_failure(target.provider, target.model, upstream.status_code,
                                                str(err.get("code") or "") or None,
                                                str(err.get("message") or "Upstream request failed"),
                                                upstream.headers.get("retry-after"))
                    await upstream.aclose()
                    health.record(target.provider, False)
                    raise failure
                buffered: list[bytes] = []
                frame: list[str] = []
                committed = False
                async def frames():
                    nonlocal committed, frame
                    async for line in upstream.aiter_lines():
                        if line == "":
                            if frame:
                                value = "\n".join(frame) + "\n\n"
                                frame = []
                                parsed = _parse_sse(value)
                                if _is_reasoning_event(parsed):
                                    continue
                                value = _sanitize_sse(value, parsed)
                                if not committed:
                                    buffered.append(value.encode())
                                    if _is_output_event(parsed):
                                        committed = True
                                        for saved in buffered:
                                            yield saved
                                        buffered.clear()
                                else:
                                    yield value.encode()
                        elif line.startswith(("data:", "event:", "id:", "retry:")):
                            frame.append(line)
                    if frame and committed:
                        yield ("\n".join(frame) + "\n\n").encode()
                iterator = frames()
                try:
                    first = await iterator.__anext__()
                except StopAsyncIteration:
                    failure = normalize_failure(target.provider, target.model, 200, "empty_stream",
                                                "Provider completed without assistant output")
                    failure.category = "DEGRADED_RESPONSE"
                    failure.retryable = True
                    health.record(target.provider, False)
                    await upstream.aclose()
                    failures.append(failure)
                    continue
                health.record(target.provider, True)
                async def relay():
                    try:
                        yield first
                        async for chunk in iterator:
                            yield chunk
                    except Exception:
                        if committed:
                            health.record(target.provider, False)
                            payload_error = {"error": {"code": "UPSTREAM_STREAM_INTERRUPTED",
                                                        "message": "The upstream stream ended unexpectedly."}}
                            yield ("event: error\ndata: " + json.dumps(payload_error) + "\n\n").encode()
                    finally:
                        await upstream.aclose()
                return StreamingResponse(relay(), media_type="text/event-stream",
                                         headers=response_headers(target, number))
            except ProviderFailure as failure:
                pass
            except (httpx.HTTPError, ValueError) as exc:
                failure = normalize_failure(target.provider, target.model, None, "transport_error", type(exc).__name__)
                health.record(target.provider, False)
            failures.append(failure)
            if not may_fallback(failure):
                return error_response(failure)
        return error_response(failures[-1] if failures else normalize_failure(
            "poolrouter", alias, 503, "no_eligible_deployment", "No eligible free provider"), exhausted=True)

    return app


def _parse_sse(frame: str) -> dict:
    event = None
    data = None
    for line in frame.splitlines():
        if line.startswith("event:"):
            event = line[6:].strip()
        elif line.startswith("data:"):
            data = line[5:].strip()
    try:
        value = json.loads(data) if data and data != "[DONE]" else {}
    except json.JSONDecodeError:
        value = {}
    return {"event": event or value.get("type"), "data": value}


def _is_reasoning_event(event: dict) -> bool:
    kind, data = event.get("event") or "", event.get("data") or {}
    return (kind.startswith("response.reasoning")
            or (data.get("item") or {}).get("type") == "reasoning"
            or (data.get("part") or {}).get("type") in {"reasoning_text", "summary_text"})


def _is_output_event(event: dict) -> bool:
    kind, data = event.get("event") or "", event.get("data") or {}
    if kind in {"response.output_text.delta", "response.function_call_arguments.delta", "response.refusal.delta"}:
        return bool(data.get("delta"))
    if kind == "response.output_item.done":
        item = data.get("item") or {}
        return item.get("type") == "function_call" or (item.get("type") == "message" and any(
            part.get("type") == "output_text" and part.get("text") for part in item.get("content", [])))
    if kind == "response.completed":
        return semantic_response_ok(data.get("response") or {})
    return False


def _sanitize_sse(frame: str, event: dict) -> str:
    data = event.get("data") or {}
    response = data.get("response")
    if isinstance(response, dict) and isinstance(response.get("output"), list):
        response["output"] = [item for item in response["output"] if item.get("type") != "reasoning"]
        data["response"] = response
        return "event: " + (event.get("event") or "message") + "\ndata: " + json.dumps(
            data, ensure_ascii=False, separators=(",", ":")) + "\n\n"
    return frame


app = create_app()
