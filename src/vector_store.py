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
PG_COLLECTION_NAME = "pg_essays"
BEZOS_COLLECTION_NAME = "bezos_letters"
EMBED_MODEL = "all-MiniLM-L6-v2"   # fast, 384-dim, good for semantic search
CHUNK_SIZE = 800       # tokens ≈ characters / 4  →  ~3 200 chars per chunk
CHUNK_OVERLAP = 150    # overlap to preserve context across boundaries
TOP_K_DEFAULT = 8


class VectorStore:
    """
    Persistent ChromaDB vector store.

    Collections:
      - acquired_transcripts : Acquired podcast episodes
      - pg_essays            : Paul Graham essays from paulgraham.com
    """

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
        self._pg_collection = self._client.get_or_create_collection(
            name=PG_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        self._bezos_collection = self._client.get_or_create_collection(
            name=BEZOS_COLLECTION_NAME,
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
    # Paul Graham Essays — Ingestion & Search
    # ------------------------------------------------------------------

    def ingest_pg_essays(self, essays: list[dict], verbose: bool = True) -> int:
        """
        Chunk and embed a list of PG essay dicts (must have 'transcript' key).
        Each essay dict: { slug, title, url, transcript }
        Returns the number of new chunks added.
        """
        total = 0
        for essay in essays:
            text = essay.get("transcript", "")
            if not text:
                continue
            chunks = _chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
            if not chunks:
                continue

            ids = [f"pg__{essay['slug']}__chunk_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "slug": essay["slug"],
                    "title": essay["title"],
                    "url": essay.get("url", ""),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                }
                for i in range(len(chunks))
            ]

            existing = set(self._pg_collection.get(ids=ids)["ids"])
            new_ids = [id_ for id_ in ids if id_ not in existing]
            if not new_ids:
                continue

            new_chunks = [chunks[ids.index(id_)] for id_ in new_ids]
            new_meta = [metadatas[ids.index(id_)] for id_ in new_ids]
            embeddings = self._embedder.encode(
                new_chunks, show_progress_bar=False
            ).tolist()

            self._pg_collection.add(
                ids=new_ids,
                documents=new_chunks,
                embeddings=embeddings,
                metadatas=new_meta,
            )

            total += len(new_ids)
            if verbose:
                print(f"  Ingested {len(new_ids)} chunks from PG: '{essay['title']}'")

        return total

    def search_pg(
        self,
        query: str,
        top_k: int = TOP_K_DEFAULT,
    ) -> list[dict]:
        """
        Semantic search over Paul Graham essays.
        Returns result dicts: { text, score, title, slug, url, chunk_index }
        """
        if self._pg_collection.count() == 0:
            return []

        query_embedding = self._embedder.encode([query])[0].tolist()
        results = self._pg_collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, max(self._pg_collection.count(), 1)),
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            hits.append(
                {
                    "text": doc,
                    "score": round(1.0 - dist, 4),
                    "title": meta.get("title", ""),
                    "slug": meta.get("slug", ""),
                    "url": meta.get("url", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                }
            )
        return hits

    def get_pg_essay_titles(self) -> list[str]:
        """Return sorted list of all unique PG essay titles in the store."""
        if self._pg_collection.count() == 0:
            return []
        all_meta = self._pg_collection.get(include=["metadatas"])["metadatas"]
        seen: set[str] = set()
        titles: list[str] = []
        for m in all_meta:
            t = m.get("title", "")
            if t and t not in seen:
                seen.add(t)
                titles.append(t)
        return sorted(titles)

    def count_pg(self) -> int:
        """Number of PG essay chunks indexed."""
        return self._pg_collection.count()

    def is_pg_empty(self) -> bool:
        return self._pg_collection.count() == 0

    # ------------------------------------------------------------------
    # Jeff Bezos Annual Shareholder Letters — Ingestion & Search
    # ------------------------------------------------------------------

    def ingest_bezos_letters(self, letters: list[dict], verbose: bool = True) -> int:
        """
        Chunk and embed a list of Bezos letter dicts (must have 'transcript' key).
        Each letter dict: { year, title, url, transcript }
        Returns the number of new chunks added.
        """
        total = 0
        for letter in letters:
            text = letter.get("transcript", "")
            if not text:
                continue
            chunks = _chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
            if not chunks:
                continue

            year = str(letter.get("year", ""))
            ids = [f"bezos__{year}__chunk_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "year": year,
                    "title": letter.get("title", f"Bezos Letter {year}"),
                    "url": letter.get("url", ""),
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                }
                for i in range(len(chunks))
            ]

            existing = set(self._bezos_collection.get(ids=ids)["ids"])
            new_ids = [id_ for id_ in ids if id_ not in existing]
            if not new_ids:
                continue

            new_chunks = [chunks[ids.index(id_)] for id_ in new_ids]
            new_meta = [metadatas[ids.index(id_)] for id_ in new_ids]
            embeddings = self._embedder.encode(
                new_chunks, show_progress_bar=False
            ).tolist()

            self._bezos_collection.add(
                ids=new_ids,
                documents=new_chunks,
                embeddings=embeddings,
                metadatas=new_meta,
            )

            total += len(new_ids)
            if verbose:
                print(f"  Ingested {len(new_ids)} chunks from Bezos letter: '{letter.get('title', year)}'")

        return total

    def search_bezos(
        self,
        query: str,
        top_k: int = TOP_K_DEFAULT,
    ) -> list[dict]:
        """
        Semantic search over Jeff Bezos shareholder letters.
        Returns result dicts: { text, score, title, year, url, chunk_index }
        """
        if self._bezos_collection.count() == 0:
            return []

        query_embedding = self._embedder.encode([query])[0].tolist()
        results = self._bezos_collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, max(self._bezos_collection.count(), 1)),
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            hits.append(
                {
                    "text": doc,
                    "score": round(1.0 - dist, 4),
                    "title": meta.get("title", ""),
                    "year": meta.get("year", ""),
                    "url": meta.get("url", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                }
            )
        return hits

    def get_bezos_letter_years(self) -> list[str]:
        """Return sorted list of all unique Bezos letter years in the store."""
        if self._bezos_collection.count() == 0:
            return []
        all_meta = self._bezos_collection.get(include=["metadatas"])["metadatas"]
        seen: set[str] = set()
        years: list[str] = []
        for m in all_meta:
            y = m.get("year", "")
            if y and y not in seen:
                seen.add(y)
                years.append(y)
        return sorted(years)

    def count_bezos(self) -> int:
        """Number of Bezos letter chunks indexed."""
        return self._bezos_collection.count()

    def is_bezos_empty(self) -> bool:
        return self._bezos_collection.count() == 0


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
