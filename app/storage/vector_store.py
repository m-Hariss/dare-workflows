import threading
from pathlib import Path

import chromadb

_COLLECTION = "workflow_files"
_lock = threading.Lock()  # prevents concurrent writes to ChromaDB
_instances: dict[str, "VectorStore"] = {}  # shared singletons keyed by data_dir path


class VectorStore:
    @classmethod
    def shared(cls, data_dir: Path) -> "VectorStore":
        """Return the single shared instance for this data directory.

        Using a shared instance means delete_all() in one part of the app
        (e.g. workflow clear) updates the same _col reference that the
        indexing pipeline uses — preventing stale collection errors.
        """
        key = str(data_dir.resolve())
        if key not in _instances:
            _instances[key] = cls(data_dir)
        return _instances[key]

    def __init__(self, data_dir: Path):
        db_path = data_dir / "chroma_db"
        db_path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(db_path))
        # cosine space: score = 1 - distance, so higher score = more similar
        self._col = self._client.get_or_create_collection(
            _COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, slot_id: str, chunks: list[str], vectors: list[list[float]]) -> None:
        """Store chunks and their vectors for a slot. Replaces any existing data for that slot."""
        if not chunks:
            return

        ids       = [f"{slot_id}::{i}" for i in range(len(chunks))]
        metadatas = [{"slot_id": slot_id, "chunk_index": i} for i in range(len(chunks))]

        with _lock:
            self._col.upsert(ids=ids, documents=chunks, embeddings=vectors, metadatas=metadatas)

    def query(
        self,
        vector: list[float],
        top_k: int = 4,
        threshold: float = 0.2,
        slot_ids: list[str] | None = None,
    ) -> list[dict]:
        """Find the most similar chunks to a query vector above the similarity threshold."""
        total = self._col.count()
        if total == 0:
            return []

        where = None
        if slot_ids and len(slot_ids) == 1:
            where = {"slot_id": slot_ids[0]}
        elif slot_ids:
            where = {"slot_id": {"$in": slot_ids}}

        n = min(top_k, total)
        results = self._col.query(
            query_embeddings=[vector],
            n_results=n,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            score = max(0.0, 1.0 - dist)  # convert cosine distance → similarity
            if score >= threshold:
                chunks.append({
                    "text":        doc,
                    "score":       round(score, 4),
                    "slot_id":     meta.get("slot_id", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                })

        return sorted(chunks, key=lambda c: c["score"], reverse=True)

    def delete(self, slot_id: str) -> None:
        """Remove all stored chunks for a slot."""
        with _lock:
            try:
                self._col.delete(where={"slot_id": slot_id})
            except Exception:
                pass  # ChromaDB raises if no documents match — safe to ignore

    def count(self) -> int:
        """Return total number of stored chunks."""
        return self._col.count()

    def delete_all(self) -> None:
        """Remove every chunk from the collection."""
        with _lock:
            try:
                self._client.delete_collection(_COLLECTION)
            except Exception:
                pass
            self._col = self._client.get_or_create_collection(
                _COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )
