"""Embedding Service — BGE-M3 powered semantic retrieval.

Uses the locally downloaded BGE-M3 model (weights/bge-m3/) to generate
dense embeddings for knowledge chunks and queries.

This replaces the stub embedding calls in the knowledge pipeline.
"""

import json
import logging
import os
from pathlib import Path
from typing import List, Optional

from dreamtalk.backend.db.database import execute, fetch

logger = logging.getLogger("dreamtalk.embeddings")

__all__ = [
    "embed_text",
    "embed_texts",
    "retrieve",
    "index_chunks",
]

# Path to BGE-M3 model weights
BGE_M3_PATH = Path(__file__).resolve().parent.parent / "weights" / "bge-m3"

# Global model instance (loaded once on first use)
_embedding_model = None
_embedding_dim = 1024  # BGE-M3 default dimension


def _get_model():
    """Lazy-load the BGE-M3 embedding model."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    if not BGE_M3_PATH.exists():
        logger.warning(
            "BGE-M3 model not found at %s. "
            "Run `python download_weights.py -c bge-m3` to download it. "
            "Falling back to zero-vector stubs.",
            BGE_M3_PATH,
        )
        return None

    try:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading BGE-M3 embedding model from %s...", BGE_M3_PATH)
        _embedding_model = SentenceTransformer(
            str(BGE_M3_PATH),
            device="cpu",
        )
        global _embedding_dim
        _embedding_dim = _embedding_model.get_sentence_embedding_dimension() or 1024
        logger.info("BGE-M3 model loaded successfully (dim=%d)", _embedding_dim)
        return _embedding_model
    except ImportError:
        logger.warning("sentence-transformers not installed. Run: pip install sentence-transformers")
        return None
    except Exception as e:
        logger.warning("Failed to load BGE-M3: %s. Using stub embeddings.", e)
        return None


async def embed_text(text: str) -> List[float]:
    """Generate embedding vector for a single text string."""
    model = _get_model()
    if model is None:
        return [0.0] * _embedding_dim

    try:
        embedding = model.encode(text, normalize_embeddings=True)
        return embedding.tolist()
    except Exception as e:
        logger.warning("Embedding failed: %s", e)
        return [0.0] * _embedding_dim


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """Generate embedding vectors for multiple texts (batched)."""
    if not texts:
        return []

    model = _get_model()
    if model is None:
        return [[0.0] * _embedding_dim for _ in texts]

    try:
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [e.tolist() for e in embeddings]
    except Exception as e:
        logger.warning("Batch embedding failed: %s", e)
        return [[0.0] * _embedding_dim for _ in texts]


async def retrieve(
    query: str,
    twin_id: str,
    top_k: int = 5,
    min_score: float = 0.5,
) -> List[dict]:
    """Retrieve relevant knowledge chunks for a query using cosine similarity.

    TODO: For large knowledge bases, consider using pgvector or batched retrieval
    instead of loading all chunks into memory.

    Args:
        query: The user's query text.
        twin_id: Digital twin ID to scope the search.
        top_k: Maximum number of chunks to return.
        min_score: Minimum similarity score threshold (default 0.5 for BGE-M3).

    Returns:
        List of dicts with 'content', 'score', 'source_name', 'source_type'.
    """
    query_embedding = await embed_text(query)
    if not any(query_embedding):  # All zeros = stub mode
        logger.info("Embedding model unavailable — returning empty retrieval")
        return []

    # Fetch all chunks for this twin
    rows = await fetch(
        """SELECT kc.id, kc.content, kc.chunk_index, kc.metadata,
                  ks.source_name, ks.source_type
           FROM knowledge_chunks kc
           JOIN knowledge_sources ks ON kc.source_id = ks.id
           WHERE kc.twin_id = $1
           ORDER BY kc.chunk_index ASC""",
        twin_id,
    )

    if not rows:
        return []

    scored = []
    for row in rows:
        chunk_meta = row["metadata"] or {}
        chunk_embedding = chunk_meta.get("embedding")

        if not chunk_embedding:
            continue

        score = _cosine_similarity(query_embedding, chunk_embedding)
        if score >= min_score:
            scored.append({
                "content": row["content"],
                "score": round(score, 4),
                "source_name": row["source_name"] or "Unknown",
                "source_type": row["source_type"] or "unknown",
                "chunk_index": row["chunk_index"],
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


async def index_chunks(twin_id: str, source_id: str, chunks: List[str]) -> int:
    """Embed and store knowledge chunks in the database.

    Args:
        twin_id: Digital twin ID.
        source_id: Knowledge source ID.
        chunks: List of text chunks to embed.

    Returns:
        Number of chunks successfully indexed.
    """
    if not chunks:
        return 0

    embeddings = await embed_texts(chunks)
    indexed = 0

    for i, (chunk_text, embedding) in enumerate(zip(chunks, embeddings)):
        metadata = json.dumps({"embedding": embedding})

        await execute(
            """UPDATE knowledge_chunks
               SET metadata = $1::jsonb
               WHERE twin_id = $2 AND source_id = $3 AND chunk_index = $4""",
            metadata,
            twin_id,
            source_id,
            i,
        )
        indexed += 1

    logger.info("Indexed %d/%d chunks for twin=%s source=%s", indexed, len(chunks), twin_id, source_id)
    return indexed


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0

    dot = sum(av * bv for av, bv in zip(a, b))
    norm_a = sum(av * av for av in a) ** 0.5
    norm_b = sum(bv * bv for bv in b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)
