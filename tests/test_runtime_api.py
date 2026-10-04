from __future__ import annotations

import json
from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient

from poolrouter.config import Settings
from poolrouter.api.app import create_app
from poolrouter.providers.openrouter import OpenRouterProvider


def settings(*, openrouter: bool = True):
    return Settings("local-secret", "groq-secret", "free", "openrouter-secret" if openrouter else "")


def headers(**extra):
    return {"Authorization": "Bearer local-secret", "X-PoolRouter-Data-Class": "public", **extra}


def test_auth_required_and_healthz_is_open():
    client = TestClient(create_app(settings(), chat_call=lambda *_: None))
    assert client.get("/healthz").status_code == 200
    assert client.get("/v1/models").status_code == 401


def test_models_lists_only_public_poolrouter_aliases():
    client = TestClient(create_app(settings(), chat_call=lambda *_: None))
    response = client.get("/v1/models", headers={"Authorization": "Bearer local-secret"})
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["data"]] == [
        "free-public", "groq-free", "openrouter-free"]


def test_empty_pool_returns_exact_free_pool_exhausted_contract():
    client = TestClient(create_app(Settings("local-secret"), chat_call=lambda *_: None))
    response = client.post("/v1/chat/completions", headers=headers(), json={
        "model": "groq-free", "messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 503
    assert response.json() == {"error": {"code": "FREE_POOL_EXHAUSTED",
        "message": "No eligible zero-cost deployment is currently available."}}


def test_public_classification_required_before_provider_calls():
    called = False
    async def chat(*_):
        nonlocal called
        called = True
    client = TestClient(create_app(settings(), chat_call=chat))
    response = client.post("/v1/chat/completions", headers={"Authorization": "Bearer local-secret"},
                           json={"model": "groq-free", "messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 403
    assert not called


def test_groq_rate_limit_falls_back_to_openrouter(monkeypatch):
    async def free_tier(self):
        return True
    monkeypatch.setattr(OpenRouterProvider, "eligible", free_tier)
    calls = []
    class UpstreamError(Exception):
        status_code = 429
        code = "rate_limit"
    async def chat(_settings, target, _payload):
        calls.append(target.provider)
        if target.provider == "groq":
            raise UpstreamError("rate limited")
        return {"id": "synthetic", "choices": [{"message": {"role": "assistant", "content": "hi",
            "reasoning_content": "private thought",
            "provider_specific_fields": {"reasoning_details": "nested private thought"}}}]}
    client = TestClient(create_app(settings(), chat_call=chat))
    response = client.post("/v1/chat/completions", headers=headers(), json={
        "model": "free-public", "messages": [{"role": "user", "content": "Say hi"}]})
    assert response.status_code == 200
    assert calls == ["groq", "openrouter"]
    assert response.headers["x-poolrouter-provider"] == "openrouter"
    assert response.headers["x-poolrouter-fallback-attempts"] == "1"
    assert response.json()["model"] == "free-public"
    assert "private thought" not in response.text
    assert "nested private thought" not in response.text


def test_auth_failure_does_not_fallback(monkeypatch):
    async def free_tier(self):
        return True
    monkeypatch.setattr(OpenRouterProvider, "eligible", free_tier)
    calls = []
    class UpstreamError(Exception):
        status_code = 401
        code = "invalid_api_key"
    async def chat(_settings, target, _payload):
        calls.append(target.provider)
        raise UpstreamError("bad key")
    client = TestClient(create_app(settings(), chat_call=chat))
    response = client.post("/v1/chat/completions", headers=headers(), json={
        "model": "free-public", "messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 401
    assert calls == ["groq"]
    assert response.json()["error"]["category"] == "AUTH"


def test_empty_completion_is_degraded_and_falls_back(monkeypatch):
    async def free_tier(self):
        return True
    monkeypatch.setattr(OpenRouterProvider, "eligible", free_tier)
    calls = []
    async def chat(_settings, target, _payload):
        calls.append(target.provider)
        if target.provider == "groq":
            return {"choices": [{"message": {"content": ""}}]}
        return {"choices": [{"message": {"content": "hi"}}]}
    client = TestClient(create_app(settings(), chat_call=chat))
    response = client.post("/v1/chat/completions", headers=headers(), json={
        "model": "free-public", "messages": [{"role": "user", "content": "hi"}]})
    assert response.status_code == 200
    assert calls == ["groq", "openrouter"]


def test_responses_strips_reasoning_and_preserves_message_contract():
    def handler(request):
        assert request.url.path.endswith("/responses")
        body = json.loads(request.content)
        assert body["model"] == "openai/gpt-oss-20b"
        assert body["store"] is False
        return httpx.Response(200, json={"id": "resp_synthetic", "object": "response", "status": "completed",
            "model": body["model"], "output": [
                {"type": "reasoning", "summary": [{"type": "summary_text", "text": "private thought"}]},
                {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "hi"}]}]})
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = TestClient(create_app(settings(openrouter=False), client=upstream))
    response = client.post("/v1/responses", headers=headers(), json={"model": "groq-free", "input": "Say hi"})
    assert response.status_code == 200
    assert response.json()["model"] == "groq-free"
    assert [item["type"] for item in response.json()["output"]] == ["message"]
    assert "private thought" not in response.text


def test_responses_stream_falls_back_before_first_output(monkeypatch):
    async def free_tier(self):
        return True
    monkeypatch.setattr(OpenRouterProvider, "eligible", free_tier)
    calls = []
    class Bytes(httpx.AsyncByteStream):
        def __init__(self, data): self.data = data
        async def __aiter__(self):
            yield self.data
    def handler(request):
        calls.append(request.url.host)
        if "groq" in request.url.host:
            return httpx.Response(200, headers={"content-type": "text/event-stream"},
                                  stream=Bytes(b"event: response.created\ndata: {\"type\":\"response.created\"}\n\nevent: response.completed\ndata: {\"type\":\"response.completed\",\"response\":{\"output\":[]}}\n\n"))
        return httpx.Response(200, headers={"content-type": "text/event-stream"},
                              stream=Bytes(b"event: response.output_text.delta\ndata: {\"type\":\"response.output_text.delta\",\"delta\":\"hi\"}\n\nevent: response.completed\ndata: {\"type\":\"response.completed\",\"response\":{\"output\":[{\"type\":\"message\"}]}}\n\n"))
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = TestClient(create_app(settings(), client=upstream))
    response = client.post("/v1/responses", headers=headers(), json={"model": "free-public", "input": "Say hi", "stream": True})
    assert response.status_code == 200
    assert calls == ["api.groq.com", "openrouter.ai"]
    assert response.headers["x-poolrouter-provider"] == "openrouter"
    assert "response.output_text.delta" in response.text


def test_responses_stream_does_not_restart_after_first_output(monkeypatch):
    async def free_tier(self):
        return True
    monkeypatch.setattr(OpenRouterProvider, "eligible", free_tier)
    calls = []
    class BrokenBytes(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"event: response.output_text.delta\ndata: {\"type\":\"response.output_text.delta\",\"delta\":\"hi\"}\n\n"
            raise httpx.ReadError("synthetic disconnect")
    def handler(request):
        calls.append(request.url.host)
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, stream=BrokenBytes())
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = TestClient(create_app(settings(), client=upstream))
    response = client.post("/v1/responses", headers=headers(), json={
        "model": "free-public", "input": "Say hi", "stream": True})
    assert response.status_code == 200
    assert calls == ["api.groq.com"]
    assert "response.output_text.delta" in response.text
    assert "UPSTREAM_STREAM_INTERRUPTED" in response.text
