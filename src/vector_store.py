"""
Vector Store — ChromaDB + sentence-transformers
Chunks Acquired transcripts and provides semantic search for the RAG pipeline.
"""

import json
import os
import textwrap
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

COLLECTION_NAME = "acquired_transcripts"
EMBED_MODEL = "all-MiniLM-L6-v2"   # fast, 384-dim, good for semantic search
CHUNK_SIZE = 800       # tokens ≈ characters / 4  →  ~3 200 chars per chunk
CHUNK_OVERLAP = 150    # overlap to preserve context across boundaries
TOP_K_DEFAULT = 8


class VectorStore:
    """Persistent ChromaDB vector store for Acquired podcast transcripts."""

    def __init__(self, db_path: str = "./data/chroma_db"):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(anonymized_telemetry=False),
        )
        self._embedder = SentenceTransformer(EMBED_MODEL)
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def is_empty(self) -> bool:
        return self._collection.count() == 0

    def ingest_episodes(self, episodes: list[dict], verbose: bool = True) -> int:
        """
        Chunk and embed a list of episode dicts (must have 'transcript' key).
        Returns the total number of chunks added.
        """
        total = 0
        for ep in episodes:
            transcript = ep.get("transcript", "")
            if not transcript:
                continue
            chunks = _chunk_text(transcript, CHUNK_SIZE, CHUNK_OVERLAP)
            if not chunks:
                continue

            ids = [f"{ep['slug']}__chunk_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "slug": ep["slug"],
                    "title": ep["title"],
                    "url": ep.get("url", ""),
                    "season": str(ep.get("season") or ""),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                }
                for i in range(len(chunks))
            ]

            # Skip chunks already stored (idempotent)
            existing = set(self._collection.get(ids=ids)["ids"])
            new_ids = [id_ for id_ in ids if id_ not in existing]
            if not new_ids:
                continue

            new_chunks = [chunks[ids.index(id_)] for id_ in new_ids]
            new_meta = [metadatas[ids.index(id_)] for id_ in new_ids]
            embeddings = self._embedder.encode(new_chunks, show_progress_bar=False).tolist()

            self._collection.add(
                ids=new_ids,
                documents=new_chunks,
                embeddings=embeddings,
                metadatas=new_meta,
            )

            total += len(new_ids)
            if verbose:
                print(f"  Ingested {len(new_ids)} chunks from '{ep['title']}'")

        return total

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(
        self,
        query: str,
        top_k: int = TOP_K_DEFAULT,
        where: Optional[dict] = None,
    ) -> list[dict]:
        """
        Semantic search over all ingested transcripts.

        Returns a list of result dicts:
          { text, score, title, slug, url, chunk_index }
        sorted by relevance (best first).
        """
        query_embedding = self._embedder.encode([query])[0].tolist()

        kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k, max(self._collection.count(), 1)),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        hits = []
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        dists = results["distances"][0]

        for doc, meta, dist in zip(docs, metas, dists):
            hits.append(
                {
                    "text": doc,
                    "score": round(1.0 - dist, 4),   # cosine distance → similarity
                    "title": meta.get("title", ""),
                    "slug": meta.get("slug", ""),
                    "url": meta.get("url", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                }
            )
        return hits

    def get_episode_slugs(self) -> list[str]:
        """Return sorted list of all unique episode slugs in the store."""
        if self._collection.count() == 0:
            return []
        all_meta = self._collection.get(include=["metadatas"])["metadatas"]
        slugs = sorted({m["slug"] for m in all_meta if m.get("slug")})
        return slugs

    def count(self) -> int:
        return self._collection.count()


# ------------------------------------------------------------------
# Text chunking helpers
# ------------------------------------------------------------------

def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Split *text* into overlapping word-level chunks of ~chunk_size words each.
    """
    words = text.split()
    if not words:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap

    return chunks
