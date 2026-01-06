"""
Exact In-Memory Vector Index.
Baseline implementation using Numpy for exact cosine similarity.
"""

from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .index import ScoredResult, Vector, VectorIndex


class ExactInMemoryIndex(VectorIndex):
    def __init__(self) -> None:
        self._data: Dict[str, np.ndarray] = {}  # type: ignore
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def upsert(self, id: str, vector: Vector, metadata: Optional[Dict[str, Any]] = None) -> None:
        # Normalize vector for cosine similarity (L2 norm)
        v = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(v)
        if norm > 0:
            v = v / norm
        self._data[id] = v
        if metadata:
            self._metadata[id] = metadata

    def delete(self, id: str) -> None:
        if id in self._data:
            del self._data[id]
        if id in self._metadata:
            del self._metadata[id]

    def query(
        self, vector: Vector, k: int = 10, filter: Optional[Dict[str, Any]] = None
    ) -> List[ScoredResult]:
        if not self._data:
            return []

        # Normalize query vector
        q = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(q)
        if norm > 0:
            q = q / norm

        scores = []
        # Linear scan (Brute force)
        for doc_id, doc_vec in self._data.items():
            # Apply Filter if present
            if filter:
                doc_meta = self._metadata.get(doc_id)
                if not doc_meta:
                    continue  # Filter present but no metadata -> skip
                # Check subset: all items in filter must equal items in doc_meta
                match = True
                for fk, fv in filter.items():
                    if doc_meta.get(fk) != fv:
                        match = False
                        break
                if not match:
                    continue

            # Dot product of normalized vectors = Cosine Similarity
            score = float(np.dot(q, doc_vec))
            scores.append((doc_id, score))

        # Sort: Score Descending, ID Ascending (Deterministic tie-break)
        # We use a tuple key: (-score, id) because Python sort is stable and ascending by default
        scores.sort(key=lambda x: (-x[1], x[0]))

        return scores[:k]

    def bulk_load(self, items: List[Tuple[str, Vector, Optional[Dict[str, Any]]]]) -> None:
        for id, vector, metadata in items:
            self.upsert(id, vector, metadata)

    def save(self, path: str) -> None:
        """
        Save index to disk.
        Creates: {path}.npz (vectors) and {path}.meta.json (metadata/ids).
        """
        import json

        # Ensure consistent ordering for save
        sorted_ids = sorted(self._data.keys())
        vectors = [self._data[id] for id in sorted_ids]

        # Save vectors
        np.savez_compressed(f"{path}.npz", vectors=np.array(vectors), ids=sorted_ids)

        # Save metadata
        meta_payload = {
            "version": "v1",
            "dim": len(vectors[0]) if vectors else 0,
            "count": len(vectors),
            "metadata": self._metadata,
        }
        with open(f"{path}.meta.json", "w") as f:
            json.dump(meta_payload, f, sort_keys=True)

    def load(self, path: str) -> None:
        """
        Load index from disk.
        Reads: {path}.npz and {path}.meta.json.
        """
        import json

        # Load vectors
        with np.load(f"{path}.npz") as data:
            ids = data["ids"]
            vectors = data["vectors"]

        # Rebuild dictionary
        self._data = {}
        for i, id_ in enumerate(ids):
            self._data[str(id_)] = vectors[i]

        # Load metadata
        try:
            with open(f"{path}.meta.json", "r") as f:
                meta_payload = json.load(f)
                # Version check
                if meta_payload.get("version") != "v1":
                    raise ValueError(f"Unknown index version: {meta_payload.get('version')}")
                self._metadata = meta_payload.get("metadata", {})
        except FileNotFoundError:
            self._metadata = {}
