# ── Weaviate Vector DB Client ─────────────────────────────────────────
# Stores and queries vector embeddings for knowledge base, memory, etc.

import os
import hashlib
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger("dreamtalk.weaviate")

WEAVIATE_URL = os.getenv("WEAVIATE_URL", "http://weaviate:8080")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY", None)

_client = None
_ready = False


def _get_client():
    global _client, _ready
    if _client is not None:
        return _client
    try:
        import weaviate
        import weaviate.classes as wvc

        auth = None
        if WEAVIATE_API_KEY:
            auth = weaviate.auth.AuthApiKey(api_key=WEAVIATE_API_KEY)

        _client = weaviate.connect_to_local(
            host=os.getenv("WEAVIATE_HOST", "weaviate"),
            port=int(os.getenv("WEAVIATE_PORT", "8080")),
            grpc_port=int(os.getenv("WEAVIATE_GRPC_PORT", "50051")),
            auth_credentials=auth,
            skip_init_checks=False,
        )
        _ready = _client.is_ready()
        if _ready:
            logger.info(f"Weaviate connected: {WEAVIATE_URL}")
            _ensure_schemas()
        else:
            logger.warning("Weaviate not ready yet")
    except Exception as e:
        logger.warning(f"Weaviate unavailable: {e}")
        _client = None
        _ready = False
    return _client


def _ensure_schemas():
    """Create required collections if they don't exist."""
    if not _client:
        return
    import weaviate.classes as wvc

    collections = {
        "KnowledgeEntry": {
            "description": "Knowledge base entries for the student persona",
            "properties": [
                wvc.config.Property(name="topic", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="language", data_type=wvc.config.DataType.TEXT),
            ],
        },
        "SessionMemory": {
            "description": "Conversation session memory for context",
            "properties": [
                wvc.config.Property(name="session_id", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="role", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="content", data_type=wvc.config.DataType.TEXT),
                wvc.config.Property(name="timestamp", data_type=wvc.config.DataType.TEXT),
            ],
        },
    }

    for name, schema in collections.items():
        try:
            if not _client.collections.exists(name):
                _client.collections.create(name, **schema)
                logger.info(f"Created Weaviate collection: {name}")
        except Exception as e:
            logger.debug(f"Weaviate schema '{name}': {e}")


async def store_embedding(
    collection: str,
    content: str,
    metadata: dict,
    vector: Optional[list] = None,
) -> Optional[str]:
    """Store an embedding in a Weaviate collection."""
    client = _get_client()
    if not client or not _ready:
        return None
    try:
        col = client.collections.get(collection)
        uuid = col.data.insert(
            properties={**metadata, "content": content},
            vector=vector,
        )
        return str(uuid)
    except Exception as e:
        logger.warning(f"Failed to store in Weaviate: {e}")
        return None


async def search_similar(
    collection: str,
    query: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Search for similar content in a Weaviate collection."""
    client = _get_client()
    if not client or not _ready:
        return []
    try:
        col = client.collections.get(collection)
        response = col.query.near_text(
            query=query,
            limit=limit,
        )
        results = []
        for obj in response.objects:
            results.append({
                "id": str(obj.uuid),
                "properties": obj.properties,
                "score": getattr(obj, "distance", None),
            })
        return results
    except Exception as e:
        logger.warning(f"Weaviate search failed: {e}")
        return []


async def health_check() -> dict:
    """Check if Weaviate is available."""
    client = _get_client()
    if not client:
        return {"available": False, "error": "Not connected"}
    try:
        ready = client.is_ready()
        meta = client.get_meta()
        return {
            "available": ready,
            "version": meta.get("version", "unknown"),
        }
    except Exception as e:
        return {"available": False, "error": str(e)}
