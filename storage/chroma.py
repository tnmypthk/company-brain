"""
ChromaDB wrapper.

Why ChromaDB? It's a local-first vector DB that runs in-process with zero
infrastructure setup — perfect for a portfolio project. You can swap it for
Pinecone or Weaviate later by replacing just this file.

Why a wrapper at all? Direct ChromaDB calls scattered through the codebase mean
every caller has to know the collection name, embedding function, and ID scheme.
Centralizing that here means one change propagates everywhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

# ChromaDB needs sqlite3 >= 3.35, but some hosts (notably Streamlit Cloud) ship
# an older system sqlite3 — which fails confusingly during client init. When
# the modern pysqlite3 build is installed (Linux/Cloud, see requirements.txt),
# swap it in for the stdlib sqlite3 BEFORE importing chromadb. On local dev
# (macOS) pysqlite3 isn't installed, so this no-ops and the system sqlite3 is
# used. Must run before `import chromadb`.
try:
    __import__("pysqlite3")
    import sys as _sys
    _sys.modules["sqlite3"] = _sys.modules.pop("pysqlite3")
except ImportError:
    pass

import chromadb
from chromadb.utils import embedding_functions

from ingestion.chunker import Chunk
from utils.config import get_config

# Vector-store settings come from config.yaml (storage:) so the DB location,
# collection name, and embedding model can be changed without editing code.
_storage_cfg = get_config()["storage"]
_DB_PATH = Path(_storage_cfg["db_path"])
_COLLECTION_NAME = _storage_cfg["collection_name"]
_EMBED_MODEL = _storage_cfg["embed_model"]

# Module-level singletons — one client, one collection per process.
_client: chromadb.PersistentClient | None = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        _DB_PATH.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(_DB_PATH))
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=_EMBED_MODEL)
        _collection = _client.get_or_create_collection(
            name=_COLLECTION_NAME,
            embedding_function=ef,
            # cosine distance works better than L2 for semantic similarity of text embeddings
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def store_chunks(chunks: List[Chunk]) -> int:
    """
    Embed and store a list of Chunk objects. Returns the number stored.

    IDs are deterministic: "{source}::chunk_{index}" so re-running ingestion on
    the same file upserts rather than duplicates. ChromaDB's add() errors on
    duplicate IDs, so we use upsert() instead.
    """
    if not chunks:
        return 0

    collection = _get_collection()

    documents = [c.text for c in chunks]
    metadatas = [c.metadata for c in chunks]
    # email_id makes Gmail chunks unique when multiple emails share the same subject
    ids = [
        f"{c.metadata.get('email_id', c.metadata['source'])}::chunk_{c.metadata['chunk_index']}"
        for c in chunks
    ]

    collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
    return len(chunks)


def query(text: str, n_results: int = 5) -> list[dict]:
    """
    Semantic search: embed the query and return the n closest chunks.

    Returns a list of dicts with keys: text, metadata, distance.
    Distance is cosine distance (0 = identical, 2 = opposite).
    """
    collection = _get_collection()
    results = collection.query(query_texts=[text], n_results=n_results)

    output = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        output.append({"text": doc, "metadata": meta, "distance": dist})

    return output


def collection_stats() -> dict:
    """Return basic stats for the dashboard."""
    collection = _get_collection()
    return {
        "total_chunks": collection.count(),
        "collection_name": _COLLECTION_NAME,
        "embed_model": _EMBED_MODEL,
        "db_path": str(_DB_PATH),
    }
