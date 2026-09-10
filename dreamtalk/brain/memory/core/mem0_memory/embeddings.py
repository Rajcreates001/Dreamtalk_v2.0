# Dreamtalk - Memory Module
# Extracted from mem0

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import tiktoken


class EmbeddingBase(ABC):
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    def embed_query(self, text: str) -> List[float]:
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        pass


class OpenAIEmbedding(EmbeddingBase):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.model = self.config.get("model", "text-embedding-3-small")
        self.dimensions_config = self.config.get("dimensions", 1536)
        self.api_key = self.config.get("api_key", "")
        self._client = None
        self._async_client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            kwargs = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            self._client = OpenAI(**kwargs)
        return self._client

    @property
    def async_client(self):
        if self._async_client is None:
            from openai import AsyncOpenAI
            kwargs = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            self._async_client = AsyncOpenAI(**kwargs)
        return self._async_client

    def embed(self, texts: List[str]) -> List[List[float]]:
        kwargs = {"model": self.model, "input": texts}
        if self.dimensions_config and self.model.startswith("text-embedding-3"):
            kwargs["dimensions"] = self.dimensions_config
        response = self.client.embeddings.create(**kwargs)
        return [item.embedding for item in response.data]

    async def aembed(self, texts: List[str]) -> List[List[float]]:
        kwargs = {"model": self.model, "input": texts}
        if self.dimensions_config and self.model.startswith("text-embedding-3"):
            kwargs["dimensions"] = self.dimensions_config
        response = await self.async_client.embeddings.create(**kwargs)
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> List[float]:
        return self.embed([text])[0]

    @property
    def dimensions(self) -> int:
        return self.dimensions_config

    def count_tokens(self, text: str) -> int:
        try:
            encoding = tiktoken.encoding_for_model(self.model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        return len(encoding.encode(text))
