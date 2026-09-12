# Dreamtalk - LLM Service
# vLLM client targeting GPU server (2x Blackwell, 192GB VRAM, Qwen3.6-27B)

import httpx
import json
import logging
import os
import re
import time
from typing import AsyncGenerator, Optional
from dreamtalk.shared.config.settings import settings
from dreamtalk.orchestration.persona.presets import DR_BC_ROY_SYSTEM_PROMPT

def _normalise_api_base(value: str) -> str:
    """Return an OpenAI-compatible API base ending in /v1.

    str.rstrip('/v1') removes any combination of those characters and can
    corrupt hostnames or ports.  Use an exact suffix check instead.
    """
    base = str(value).rstrip("/")
    return base if base.endswith("/v1") else f"{base}/v1"


GPU_API_BASE = _normalise_api_base(settings.GPU_SERVER_BASE_URL)
GPU_SERVER_URL = GPU_API_BASE[:-3]
API_KEY = settings.GPU_SERVER_API_KEY
MODEL_NAME = settings.LLM_MODEL_NAME
logger = logging.getLogger("dreamtalk.llm")


# ── endpoint circuit breaker ──────────────────────────────────────────
# A single reply makes several LLM calls (emotion, generation, translation).
# When the primary endpoint is down, each of them paid the full connect
# timeout before falling back, adding tens of seconds to every utterance.
# Remember a failure briefly and skip that endpoint instead of re-probing it.
_ENDPOINT_COOLDOWN_S = float(os.environ.get("LLM_ENDPOINT_COOLDOWN", "300"))
_endpoint_down_until: dict[str, float] = {}


def _mark_endpoint_down(api_base: str) -> None:
    _endpoint_down_until[api_base] = time.monotonic() + _ENDPOINT_COOLDOWN_S
    logger.warning("LLM endpoint %s marked down for %.0fs", api_base, _ENDPOINT_COOLDOWN_S)


def _mark_endpoint_up(api_base: str) -> None:
    if _endpoint_down_until.pop(api_base, None) is not None:
        logger.info("LLM endpoint %s recovered", api_base)


def _candidate_endpoints() -> list[tuple[str, str]]:
    candidates = [(GPU_API_BASE, MODEL_NAME)]
    fallback_url = os.environ.get("LLM_FALLBACK_BASE_URL", "http://host.docker.internal:11434/v1")
    fallback_model = os.environ.get("LLM_FALLBACK_MODEL", "llama3.1:8b")
    fallback = (_normalise_api_base(fallback_url), fallback_model)
    if fallback not in candidates:
        candidates.append(fallback)
    now = time.monotonic()
    live = [(b, m) for (b, m) in candidates if _endpoint_down_until.get(b, 0.0) <= now]
    # If everything is cooling down, try them all rather than fail outright.
    return live or candidates


def _clean_response(content: str) -> str:
    return re.sub(r"<think>.*?</think>", "", content or "", flags=re.DOTALL).strip()


async def chat_completion(
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 1024,
    stream: bool = False,
    system_prompt: Optional[str] = None,
) -> dict | AsyncGenerator[str, None]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    } if API_KEY else {
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "system", "content": system_prompt or DR_BC_ROY_SYSTEM_PROMPT}, *messages],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }

    if stream:
        # The generator owns its client. Returning a generator from inside an
        # AsyncClient context closes the client before streaming begins.
        return _stream_response(_candidate_endpoints(), headers, payload)

    timeout = float(getattr(settings, "LLM_TIMEOUT", 120.0) or 120.0)
    errors = []
    client_timeout = httpx.Timeout(timeout, connect=min(5.0, timeout))
    async with httpx.AsyncClient(timeout=client_timeout) as client:
        for api_base, model in _candidate_endpoints():
            current_payload = {**payload, "model": model}
            try:
                response = await client.post(
                    f"{api_base}/chat/completions",
                    headers=headers,
                    json=current_payload,
                )
                response.raise_for_status()
                data = response.json()
                _mark_endpoint_up(api_base)
                return {
                    "response": _clean_response(data["choices"][0]["message"]["content"]),
                    "model": data.get("model", model),
                    "usage": data.get("usage", {}),
                    "api_base": api_base,
                }
            except Exception as exc:
                errors.append(f"{model}@{api_base}: {type(exc).__name__}: {exc}")
                logger.warning("LLM endpoint failed: %s", errors[-1])
                _mark_endpoint_down(api_base)
    raise RuntimeError("All configured LLM endpoints failed: " + " | ".join(errors))


async def _stream_response(
    endpoints: list[tuple[str, str]],
    headers: dict,
    payload: dict,
) -> AsyncGenerator[str, None]:
    timeout = float(getattr(settings, "LLM_TIMEOUT", 120.0) or 120.0)
    errors = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=min(5.0, timeout))) as client:
        for api_base, model in endpoints:
            current_payload = {**payload, "model": model}
            try:
                async with client.stream(
                    "POST", f"{api_base}/chat/completions", headers=headers, json=current_payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            chunk = line[6:].strip()
                            if chunk == "[DONE]":
                                return
                            try:
                                data = json.loads(chunk)
                                content = data["choices"][0].get("delta", {}).get("content", "")
                                if content:
                                    yield content
                            except (json.JSONDecodeError, KeyError, IndexError):
                                continue
                    return
            except Exception as exc:
                errors.append(f"{model}@{api_base}: {type(exc).__name__}: {exc}")
                logger.warning("Streaming LLM endpoint failed: %s", errors[-1])
                _mark_endpoint_down(api_base)
    raise RuntimeError("All configured streaming LLM endpoints failed: " + " | ".join(errors))


async def check_gpu_server_health() -> dict:
    checks = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(5.0, connect=3.0)) as client:
        for api_base, model in _candidate_endpoints():
            try:
                response = await client.get(f"{api_base}/models")
                response.raise_for_status()
                data = response.json()
                models = [item["id"] for item in data.get("data", [])]
                return {
                    "status": "online",
                    "url": api_base,
                    "models": models,
                    "active_model": model,
                    "fallback": api_base != GPU_API_BASE,
                    "checks": checks,
                }
            except Exception as exc:
                checks.append({"url": api_base, "model": model, "error": f"{type(exc).__name__}: {exc}"})
    return {"status": "offline", "checks": checks}
