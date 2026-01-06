"""
Embedding Provider Interface & Implementations.
"""

from abc import ABC, abstractmethod
from typing import List

import numpy as np


class EmbeddingProvider(ABC):
    """
    Abstract base for embedding providers.
    """

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Batch embed texts."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return vector dimension."""
        pass


class DeterministicStubProvider(EmbeddingProvider):
    """
    Deterministic has-based embeddings for testing.
    Uses MD5 + RandomState to project text to fixed 384d vector.
    """

    def __init__(self, dim: int = 384):
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        results = []
        for text in texts:
            # Hash to see
            import hashlib

            h = hashlib.md5(text.encode("utf8")).hexdigest()
            # Use chunks of hash to salt the seed?
            # Simple approach: first 8 chars hex -> int
            seed = int(h[:8], 16)

            rng = np.random.RandomState(seed)
            vec = rng.randn(self._dim)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            results.append(vec.tolist())
        return results
