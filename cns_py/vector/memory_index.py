"""
Exact In-Memory Vector Index.
Baseline implementation using Numpy for exact cosine similarity.
"""
import numpy as np
from typing import List, Optional, Dict, Tuple, Any
from .index import VectorIndex, Vector, ScoredResult

class ExactInMemoryIndex(VectorIndex):
    def __init__(self):
        self._data: Dict[str, np.ndarray] = {}
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

    def query(self, vector: Vector, k: int = 10, filter: Optional[Dict[str, Any]] = None) -> List[ScoredResult]:
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
