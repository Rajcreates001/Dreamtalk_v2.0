# Dreamtalk - LLM Service
# vLLM client targeting GPU server (2x Blackwell, 192GB VRAM, Qwen3.6-27B)

import httpx
import json
from typing import AsyncGenerator
from dreamtalk.shared.config.settings import settings
from dreamtalk.orchestration.persona.presets import DR_BC_ROY_SYSTEM_PROMPT

GPU_SERVER_URL = settings.GPU_SERVER_BASE_URL.rstrip("/v1").rstrip("/")
API_KEY = settings.GPU_SERVER_API_KEY
MODEL_NAME = settings.LLM_MODEL_NAME


async def chat_completion(
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 1024,
    stream: bool = False,
) -> dict | AsyncGenerator[str, None]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    } if API_KEY else {
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "system", "content": DR_BC_ROY_SYSTEM_PROMPT}, *messages],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": stream,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        if stream:
            return _stream_response(client, f"{GPU_SERVER_URL}/v1/chat/completions", headers, payload)

        response = await client.post(
            f"{GPU_SERVER_URL}/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "response": data["choices"][0]["message"]["content"],
            "model": data["model"],
            "usage": data.get("usage", {}),
        }


async def _stream_response(
    client: httpx.AsyncClient,
    url: str,
    headers: dict,
    payload: dict,
) -> AsyncGenerator[str, None]:
    async with client.stream("POST", url, headers=headers, json=payload) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                chunk = line[6:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    data = json.loads(chunk)
                    delta = data["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue


async def check_gpu_server_health() -> dict:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{GPU_SERVER_URL}/v1/models")
            response.raise_for_status()
            data = response.json()
            models = [m["id"] for m in data.get("data", [])]
            return {
                "status": "online",
                "url": GPU_SERVER_URL,
                "models": models,
                "active_model": MODEL_NAME,
            }
    except Exception as e:
        return {
            "status": "offline",
            "url": GPU_SERVER_URL,
            "error": str(e),
        }
