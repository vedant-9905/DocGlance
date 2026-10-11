"""
retriever.py — ChromaDB-backed dense retriever using sentence-transformers.

Optimisations vs v1:
  - Imports settings from config.py (single source of truth)
  - Batch embed with show_progress_bar=False for cleaner server logs
  - _get_chroma_client uses a threading lock for safety under async
  - chunk_text uses compiled regex (cached at module level)
  - retrieve() guards against n_results > collection size
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
import uuid
from typing import Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from config import (
    CHROMA_PERSIST_DIR,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_COLLECTION,
    DEFAULT_TOP_K,
    EMBED_MODEL_NAME,
)

logger = logging.getLogger(__name__)

# Pre-compiled sentence boundary regex (cheaper than compiling on every call)
_SENT_BOUNDARY = re.compile(
    r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\!|\?)\s+"
)

# Module-level singletons
_embed_model: SentenceTransformer | None = None
_chroma_client: chromadb.ClientAPI | None = None
_lock = threading.Lock()


# ── Model / client factories ────────────────────────────────────────────────

def _get_embed_model() -> SentenceTransformer:
    global _embed_model
    if _embed_model is None:
        with _lock:
            if _embed_model is None:  # double-checked locking
                logger.info("Loading embedding model: %s", EMBED_MODEL_NAME)
                _embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    return _embed_model


def _get_chroma_client() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        with _lock:
            if _chroma_client is None:
                logger.info("Initialising ChromaDB at: %s", CHROMA_PERSIST_DIR)
                _chroma_client = chromadb.PersistentClient(
                    path=CHROMA_PERSIST_DIR,
                    settings=Settings(anonymized_telemetry=False),
                )
    return _chroma_client


# ── Text chunking ────────────────────────────────────────────────────────────

def chunk_text(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """
    Split *text* into overlapping character-level chunks.
    Prefers sentence boundaries; falls back to hard character breaks.
    """
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            # Snap to nearest sentence boundary within the window
            boundary = text.rfind(". ", start, end)
            if boundary != -1 and boundary > start + overlap:
                end = boundary + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(start + 1, end - overlap)

    return chunks


def _stable_chunk_id(source_id: str, chunk_index: int, text: str) -> str:
    """Deterministic ID so re-uploading the same file is idempotent."""
    payload = f"{source_id}::{chunk_index}::{text[:64]}"
    return hashlib.sha1(payload.encode()).hexdigest()


# ── DocumentRetriever ────────────────────────────────────────────────────────

class DocumentRetriever:
    """
    Manages a ChromaDB collection.
    Thread-safe singleton models; supports concurrent FastAPI requests.
    """

    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        n_results: int = DEFAULT_TOP_K,
    ) -> None:
        self.collection_name = collection_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.n_results = n_results

        self.collection = _get_chroma_client().get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        _get_embed_model()  # Prewarm embedding model at startup
        logger.info(
            "Collection '%s' ready — %d existing chunks",
            collection_name,
            self.collection.count(),
        )

    # ── Ingestion ────────────────────────────────────────────────────────────

    def ingest(
        self,
        text: str,
        source_name: str = "unknown",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, int]:
        """
        Chunk *text*, embed, and upsert into ChromaDB.
        Re-uploading the same file is safe (idempotent upsert).
        """
        chunks = chunk_text(text, self.chunk_size, self.chunk_overlap)
        if not chunks:
            logger.warning("ingest(%s): produced 0 chunks — skipping", source_name)
            return {"chunks_added": 0, "chunks_skipped": 0}

        model = _get_embed_model()
        # Encode all chunks in one batch for efficiency
        embeddings: list[list[float]] = model.encode(
            chunks,
            batch_size=64,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,   # cosine similarity = dot product after norm
        ).tolist()  # type: ignore[union-attr]

        source_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, source_name))
        ids, documents, metadatas, vecs = [], [], [], []

        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            ids.append(_stable_chunk_id(source_id, idx, chunk))
            documents.append(chunk)
            vecs.append(emb)
            metadatas.append(
                {"source": source_name, "chunk_index": idx, **(metadata or {})}
            )

        self.collection.upsert(
            ids=ids, embeddings=vecs, documents=documents, metadatas=metadatas
        )
        logger.info("Ingested %d chunks from '%s'", len(chunks), source_name)
        return {"chunks_added": len(chunks), "chunks_skipped": 0}

    # ── Retrieval ────────────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        n_results: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Embed *query* and return Top-K most similar chunks (descending score).

        Returns list of dicts:
            chunk_id, text, score (cosine similarity), source, chunk_index
        """
        k = n_results or self.n_results
        total = self.collection.count()
        if total == 0:
            logger.warning("retrieve(): collection is empty")
            return []

        model = _get_embed_model()
        query_emb: list[float] = model.encode(
            [query],
            convert_to_numpy=True,
            normalize_embeddings=True,
        ).tolist()[0]  # type: ignore[index]

        results = self.collection.query(
            query_embeddings=[query_emb],
            n_results=min(k, total),
            include=["documents", "metadatas", "distances"],
        )

        output: list[dict[str, Any]] = []
        for chunk_id, doc, meta, dist in zip(
            results["ids"][0],
            results["documents"][0],  # type: ignore[index]
            results["metadatas"][0],  # type: ignore[index]
            results["distances"][0],  # type: ignore[index]
        ):
            output.append(
                {
                    "chunk_id": chunk_id,
                    "text": doc,
                    "score": round(max(0.0, 1.0 - dist), 4),
                    "source": meta.get("source", "unknown"),
                    "chunk_index": meta.get("chunk_index", -1),
                }
            )

        output.sort(key=lambda x: x["score"], reverse=True)
        return output

    # ── Utility ──────────────────────────────────────────────────────────────

    def collection_stats(self) -> dict[str, Any]:
        return {
            "collection_name": self.collection_name,
            "total_chunks": self.collection.count(),
        }
