# Dreamtalk - Memory Module
# Extracted from mem0

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np


def bm25_sigmoid_score(raw_score: float, k: float = 0.5) -> float:
    return 1.0 / (1.0 + math.exp(-k * (raw_score - 0.5)))


def hybrid_score(
    semantic_score: float,
    bm25_score: float,
    entity_boost: float = 0.0,
    semantic_weight: float = 0.5,
    bm25_weight: float = 0.3,
    entity_weight: float = 0.2,
) -> float:
    return (
        semantic_weight * semantic_score
        + bm25_weight * bm25_score
        + entity_weight * entity_boost
    )


class LlmFactory:
    @staticmethod
    def create(config: Dict[str, Any]):
        provider = config.get("provider", "openai").lower()
        model = config.get("model", "gpt-4o-mini")
        api_key = config.get("api_key", "")
        kwargs = {k: v for k, v in config.items() if k not in ("provider", "model", "api_key")}
        if provider == "openai":
            from openai import OpenAI
            client_kwargs = {}
            if api_key:
                client_kwargs["api_key"] = api_key
            client = OpenAI(**client_kwargs)
            return client, model
        elif provider == "anthropic":
            from anthropic import Anthropic
            client = Anthropic(api_key=api_key) if api_key else Anthropic()
            return client, model
        elif provider == "groq":
            from groq import Groq
            client = Groq(api_key=api_key) if api_key else Groq()
            return client, model
        elif provider == "ollama":
            from openai import OpenAI
            base_url = kwargs.get("base_url", "http://localhost:11434/v1")
            client = OpenAI(base_url=base_url, api_key="ollama")
            return client, model
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")


class EmbeddingFactory:
    @staticmethod
    def create(config: Dict[str, Any]):
        provider = config.get("provider", "openai").lower()
        if provider == "openai":
            from dreamtalk.brain.memory.core.mem0_memory.embeddings import OpenAIEmbedding
            return OpenAIEmbedding(config)
        elif provider == "azure":
            from dreamtalk.brain.memory.core.mem0_memory.embeddings import OpenAIEmbedding
            return OpenAIEmbedding({**config, "model": config.get("deployment_name", "text-embedding-3-small")})
        elif provider == "ollama":
            from openai import OpenAI
            base_url = config.get("base_url", "http://localhost:11434/v1")
            model = config.get("model", "nomic-embed-text")
            client = OpenAI(base_url=base_url, api_key="ollama")

            class OllamaEmbedding:
                def __init__(self, client, model, dims):
                    self._client = client
                    self._model = model
                    self._dimensions = dims

                def embed(self, texts):
                    resp = self._client.embeddings.create(model=self._model, input=texts)
                    return [item.embedding for item in resp.data]

                def embed_query(self, text):
                    return self.embed([text])[0]

                @property
                def dimensions(self):
                    return self._dimensions

            return OllamaEmbedding(client, model, config.get("dimensions", 768))
        else:
            raise ValueError(f"Unsupported embedding provider: {provider}")
