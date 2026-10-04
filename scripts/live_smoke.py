"""Manual smoke matrix against the local gateway; never prints prompt/body/secrets."""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from poolrouter.config import load_local_env


BASE = os.getenv("POOLROUTER_BASE_URL", "http://127.0.0.1:4000")
TOOL = {"type": "function", "function": {"name": "greet", "description": "Return a greeting",
        "parameters": {"type": "object", "properties": {"message": {"type": "string"}},
                       "required": ["message"], "additionalProperties": False}}}


def main() -> int:
    load_local_env(Path.cwd() / ".env")
    token = os.getenv("POOLROUTER_API_KEY", "")
    if not token:
        print("blocked: local bearer key is not configured")
        return 2
    headers = {"Authorization": f"Bearer {token}", "X-PoolRouter-Data-Class": "public"}
    rows: list[tuple[str, bool]] = []
    with httpx.Client(timeout=180) as client:
        for alias in ("groq-free", "openrouter-free"):
            rows.append(run_json(client, headers, f"{alias} chat", "/v1/chat/completions", {
                "model": alias, "messages": [{"role": "user", "content": "Say hi briefly."}], "max_tokens": 96
            }, lambda b: bool((b.get("choices") or [{}])[0].get("message", {}).get("content"))))
            rows.append(run_stream(client, headers, f"{alias} chat stream", "/v1/chat/completions", {
                "model": alias, "messages": [{"role": "user", "content": "Say hi briefly."}],
                "max_tokens": 96, "stream": True
            }, "chat"))
            rows.append(run_json(client, headers, f"{alias} chat tool", "/v1/chat/completions", {
                "model": alias, "messages": [{"role": "user", "content": "Call greet with message hi."}],
                "tools": [TOOL], "tool_choice": {"type": "function", "function": {"name": "greet"}},
                "max_tokens": 128
            }, lambda b: bool((b.get("choices") or [{}])[0].get("message", {}).get("tool_calls"))))
            rows.append(run_json(client, headers, f"{alias} responses", "/v1/responses", {
                "model": alias, "input": "Say hi briefly.", "max_output_tokens": 256
            }, responses_ok))
            rows.append(run_stream(client, headers, f"{alias} responses stream", "/v1/responses", {
                "model": alias, "input": "Say hi briefly.", "max_output_tokens": 256, "stream": True
            }, "responses"))
            rows.append(run_json(client, headers, f"{alias} responses tool", "/v1/responses", {
                "model": alias, "input": "Call greet with message hi.", "max_output_tokens": 256,
                "tools": [{"type": "function", "name": "greet", "description": "Return a greeting",
                           "parameters": TOOL["function"]["parameters"]}],
                "tool_choice": {"type": "function", "name": "greet"}
            }, responses_tool_ok))
    for name, ok in rows:
        print(f"{'PASS' if ok else 'FAIL'} {name}")
    return 0 if all(ok for _, ok in rows) else 1


def run_json(client, headers, name, path, payload, predicate):
    try:
        response = client.post(BASE + path, headers=headers, json=payload)
        body = response.json() if response.is_success else {}
        return name, response.status_code == 200 and predicate(body)
    except (httpx.HTTPError, ValueError, TypeError):
        return name, False


def run_stream(client, headers, name, path, payload, kind):
    try:
        with client.stream("POST", BASE + path, headers=headers, json=payload) as response:
            if response.status_code != 200:
                return name, False
            saw_output = False
            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue
                text = line[6:]
                if text == "[DONE]":
                    continue
                try:
                    event = json.loads(text)
                except ValueError:
                    continue
                if kind == "chat":
                    delta = ((event.get("choices") or [{}])[0].get("delta") or {})
                    saw_output |= bool(delta.get("content") or delta.get("tool_calls"))
                else:
                    saw_output |= event.get("type") in {"response.output_text.delta",
                        "response.function_call_arguments.delta", "response.refusal.delta"}
            return name, saw_output
    except httpx.HTTPError:
        return name, False


def responses_ok(body):
    return any(item.get("type") == "message" and any(
        part.get("type") == "output_text" and part.get("text") for part in item.get("content", []))
        for item in body.get("output", []))


def responses_tool_ok(body):
    return any(item.get("type") == "function_call" and item.get("name") == "greet"
               for item in body.get("output", []))


if __name__ == "__main__":
    raise SystemExit(main())
