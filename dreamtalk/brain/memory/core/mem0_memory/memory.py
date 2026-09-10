# Dreamtalk - Memory Module
# Extracted from mem0

from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
import time
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel

from dreamtalk.brain.memory.core.mem0_memory.config import (
    FACT_RETRIEVAL_PROMPT,
    ADDITIVE_EXTRACTION_PROMPT,
    MemoryConfig,
    MemoryItem,
    MemoryType,
)
from dreamtalk.brain.memory.core.mem0_memory.embeddings import EmbeddingBase, OpenAIEmbedding
from dreamtalk.brain.memory.core.mem0_memory.utils import LlmFactory, EmbeddingFactory, hybrid_score

logger = logging.getLogger(__name__)


class MemoryBase(ABC):
    @abstractmethod
    def add(self, data: str, **kwargs) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def update(self, memory_id: str, data: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        pass

    @abstractmethod
    def history(self, memory_id: str) -> List[Dict[str, Any]]:
        pass


class VectorStoreBase(ABC):
    @abstractmethod
    def create_collection(self, name: str, embedding_dim: int):
        pass

    @abstractmethod
    def insert(self, collection: str, vectors: List[List[float]], metadata: List[Dict[str, Any]], ids: List[str]):
        pass

    @abstractmethod
    def search(self, collection: str, query_vector: List[float], limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def delete(self, collection: str, ids: List[str]):
        pass

    @abstractmethod
    def get(self, collection: str, id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def list_collections(self) -> List[str]:
        pass


class ChromaVectorStore(VectorStoreBase):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.collection_name = self.config.get("collection_name", "dreamtalk")
        self.persist_dir = self.config.get("persist_dir", None)
        self._client = None
        self._collections: Dict[str, Any] = {}

    @property
    def client(self):
        if self._client is None:
            import chromadb
            kwargs = {}
            if self.persist_dir:
                kwargs["persist_directory"] = self.persist_dir
            self._client = chromadb.PersistentClient(**kwargs) if self.persist_dir else chromadb.Client()
        return self._client

    def _get_or_create_collection(self, name: str, embedding_dim: int = 1536):
        if name not in self._collections:
            try:
                collection = self.client.get_collection(name)
            except ValueError:
                collection = self.client.create_collection(name)
            self._collections[name] = collection
        return self._collections[name]

    def create_collection(self, name: str, embedding_dim: int = 1536):
        self._get_or_create_collection(name, embedding_dim)

    def insert(self, collection: str, vectors: List[List[float]], metadata: List[Dict[str, Any]], ids: List[str]):
        col = self._get_or_create_collection(collection)
        col.add(embeddings=vectors, metadatas=metadata, ids=ids)

    def search(self, collection: str, query_vector: List[float], limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        col = self._get_or_create_collection(collection)
        kwargs = {"query_embeddings": [query_vector], "n_results": limit}
        if filters:
            kwargs["where"] = filters
        results = col.query(**kwargs)
        output = []
        for i in range(len(results["ids"][0])):
            output.append({
                "id": results["ids"][0][i],
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "score": 1.0 - results["distances"][0][i] if results["distances"] else 0.0,
            })
        return output

    def delete(self, collection: str, ids: List[str]):
        col = self._get_or_create_collection(collection)
        col.delete(ids=ids)

    def get(self, collection: str, id: str) -> Optional[Dict[str, Any]]:
        col = self._get_or_create_collection(collection)
        results = col.get(ids=[id])
        if results["ids"]:
            return {"id": results["ids"][0], "metadata": results["metadatas"][0] if results["metadatas"] else {}}
        return None

    def list_collections(self) -> List[str]:
        return [c.name for c in self.client.list_collections()]


class MemoryStorageBase(ABC):
    @abstractmethod
    def store(self, memory_id: str, data: str, metadata: Dict[str, Any]):
        pass

    @abstractmethod
    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_history(self, memory_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def update(self, memory_id: str, data: str):
        pass

    @abstractmethod
    def delete(self, memory_id: str):
        pass


class SQLiteStorage(MemoryStorageBase):
    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    data TEXT,
                    metadata TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_id TEXT,
                    data TEXT,
                    metadata TEXT,
                    timestamp TEXT,
                    action TEXT
                )
            """)
            self.conn.commit()

    def store(self, memory_id: str, data: str, metadata: Dict[str, Any]):
        now = datetime.utcnow().isoformat()
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO memories (id, data, metadata, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (memory_id, data, json.dumps(metadata), now, now),
            )
            self.conn.execute(
                "INSERT INTO memory_history (memory_id, data, metadata, timestamp, action) VALUES (?, ?, ?, ?, ?)",
                (memory_id, data, json.dumps(metadata), now, "store"),
            )
            self.conn.commit()

    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            cursor = self.conn.execute("SELECT id, data, metadata, created_at, updated_at FROM memories WHERE id = ?", (memory_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "data": row[1],
                    "metadata": json.loads(row[2]) if row[2] else {},
                    "created_at": row[3],
                    "updated_at": row[4],
                }
            return None

    def get_history(self, memory_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            cursor = self.conn.execute(
                "SELECT memory_id, data, metadata, timestamp, action FROM memory_history WHERE memory_id = ? ORDER BY id",
                (memory_id,),
            )
            return [
                {
                    "memory_id": row[0],
                    "data": row[1],
                    "metadata": json.loads(row[2]) if row[2] else {},
                    "timestamp": row[3],
                    "action": row[4],
                }
                for row in cursor.fetchall()
            ]

    def update(self, memory_id: str, data: str):
        now = datetime.utcnow().isoformat()
        with self._lock:
            self.conn.execute("UPDATE memories SET data = ?, updated_at = ? WHERE id = ?", (data, now, memory_id))
            self.conn.execute(
                "INSERT INTO memory_history (memory_id, data, timestamp, action) VALUES (?, ?, ?, ?)",
                (memory_id, data, now, "update"),
            )
            self.conn.commit()

    def delete(self, memory_id: str):
        now = datetime.utcnow().isoformat()
        with self._lock:
            self.conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            self.conn.execute(
                "INSERT INTO memory_history (memory_id, data, timestamp, action) VALUES (?, '', ?, ?)",
                (memory_id, now, "delete"),
            )
            self.conn.commit()


class Memory(MemoryBase):
    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self._embedding_model: Optional[EmbeddingBase] = None
        self._vector_store: Optional[VectorStoreBase] = None
        self._storage: Optional[MemoryStorageBase] = None
        self._llm_client = None
        self._llm_model = None
        self._watchers: List[Callable] = []
        self._lock = threading.RLock()

    @property
    def embedding_model(self) -> EmbeddingBase:
        if self._embedding_model is None:
            self._embedding_model = EmbeddingFactory.create(self.config.embedder)
        return self._embedding_model

    @property
    def vector_store(self) -> VectorStoreBase:
        if self._vector_store is None:
            vs_config = self.config.vector_store
            provider = vs_config.get("provider", "chroma").lower()
            if provider == "chroma":
                self._vector_store = ChromaVectorStore(vs_config.get("config", {}))
            else:
                raise ValueError(f"Unsupported vector store provider: {provider}")
        return self._vector_store

    @property
    def storage(self) -> MemoryStorageBase:
        if self._storage is None:
            db_config = self.config.history_db or {}
            db_path = db_config.get("path", ":memory:")
            self._storage = SQLiteStorage(db_path)
        return self._storage

    @property
    def llm(self) -> Tuple[Any, str]:
        if self._llm_client is None:
            llm_config = self.config.llm or {"provider": "openai", "model": "gpt-4o-mini"}
            self._llm_client, self._llm_model = LlmFactory.create(llm_config)
        return self._llm_client, self._llm_model

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def _hash_text(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def _get_collection_name(self, user_id: Optional[str] = None, agent_id: Optional[str] = None) -> str:
        parts = ["dreamtalk"]
        if user_id:
            parts.append(f"u_{self._hash_text(user_id)[:8]}")
        if agent_id:
            parts.append(f"a_{self._hash_text(agent_id)[:8]}")
        return "_".join(parts)

    def _extract_memory(self, data: str, existing_memories: Optional[List[str]] = None) -> str:
        client, model = self.llm
        prompt = FACT_RETRIEVAL_PROMPT
        if existing_memories:
            prompt += f"\n\nExisting memories:\n{json.dumps(existing_memories, indent=2)}"
        prompt += f"\n\nInput: {data}\n\nOutput:"

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    def add(self, data: str, user_id: Optional[str] = None, agent_id: Optional[str] = None, session_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        with self._lock:
            collection = self._get_collection_name(user_id, agent_id)
            metadata = metadata or {}

            if user_id:
                metadata["user_id"] = user_id
            if agent_id:
                metadata["agent_id"] = agent_id
            if session_id:
                metadata["session_id"] = session_id
            metadata["created_at"] = datetime.utcnow().isoformat()

            extracted = self._extract_memory(data, None)
            memory_id = self._generate_id()

            embedding = self.embedding_model.embed([data])[0]

            self.vector_store.insert(
                collection,
                [embedding],
                [{"text": data, "extracted": extracted, **metadata}],
                [memory_id],
            )
            self.storage.store(memory_id, data, {"extracted": extracted, **metadata})

            result = [{"id": memory_id, "text": data, "metadata": metadata}]

            for watcher in self._watchers:
                watcher(result)

            return result

    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        record = self.storage.get(memory_id)
        if record:
            metadata = json.loads(record["metadata"]) if isinstance(record.get("metadata"), str) else record.get("metadata", {})
            return MemoryItem(id=record["id"], text=record["data"], metadata=metadata).model_dump()
        return None

    def search(self, query: str, user_id: Optional[str] = None, agent_id: Optional[str] = None, limit: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        collection = self._get_collection_name(user_id, agent_id)
        query_embedding = self.embedding_model.embed_query(query)
        results = self.vector_store.search(collection, query_embedding, limit=limit, filters=filters)
        return [
            MemoryItem(id=r["id"], text=r["metadata"].get("text", ""), metadata=r["metadata"], score=r.get("score")).model_dump()
            for r in results
        ]

    def update(self, memory_id: str, data: str) -> Dict[str, Any]:
        with self._lock:
            existing = self.storage.get(memory_id)
            if not existing:
                raise ValueError(f"Memory {memory_id} not found")

            self.storage.update(memory_id, data)
            metadata = json.loads(existing["metadata"]) if isinstance(existing.get("metadata"), str) else existing.get("metadata", {})

            return MemoryItem(id=memory_id, text=data, metadata=metadata).model_dump()

    def delete(self, memory_id: str) -> bool:
        with self._lock:
            self.storage.delete(memory_id)
            collection = self._get_collection_name()
            try:
                self.vector_store.delete(collection, [memory_id])
            except Exception:
                pass
            return True

    def history(self, memory_id: str) -> List[Dict[str, Any]]:
        return self.storage.get_history(memory_id)

    def watch(self, callback: Callable):
        self._watchers.append(callback)

    def clear_watchers(self):
        self._watchers.clear()

    def reset(self):
        with self._lock:
            self._vector_store = None
            self._storage = None
            self._embedding_model = None
