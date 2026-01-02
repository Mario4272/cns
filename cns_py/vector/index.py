"""
Vector Index Interface (Phase 6 Slice 2)
Contract for vector storage and retrieval.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

Vector = List[float]
ScoredResult = Tuple[str, float]  # (id, score)


class VectorIndex(ABC):
    """
    Abstract base class for vector indices.
    All implementations must be deterministic in tie-breaking.
    Standard Metric: Cosine Similarity (or normalized Dot Product).
    """

    @abstractmethod
    def upsert(self, id: str, vector: Vector, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Insert or update a vector.
        :param id: Unique identifier for the item.
        :param vector: Embedding vector (list of floats).
        :param metadata: Optional metadata dict.
        """
        pass

    @abstractmethod
    def delete(self, id: str) -> None:
        """
        Remove a vector by ID.
        :param id: ID to remove.
        """
        pass

    @abstractmethod
    def query(
        self, vector: Vector, k: int = 10, filter: Optional[Dict[str, Any]] = None
    ) -> List[ScoredResult]:
        """
        Find k-nearest neighbors.
        :param vector: Query vector.
        :param k: Number of results to return.
        :param filter: Optional filter criteria (implementation dependent).
        :return: List of (id, score) tuples, sorted by score desc, then id asc.
        """
        pass

    @abstractmethod
    def bulk_load(self, items: List[Tuple[str, Vector, Optional[Dict[str, Any]]]]) -> None:
        """
        Efficiently load multiple items.
        :param items: List of (id, vector, metadata) tuples.
        """
        pass

    @abstractmethod
    def save(self, path: str) -> None:
        """
        Persist the index to disk.
        :param path: Directory or file path prefix to save to.
        """
        pass

    @abstractmethod
    def load(self, path: str) -> None:
        """
        Load the index from disk.
        :param path: Directory or file path prefix to load from.
        """
        pass
