
import logging
import os
import pickle
from typing import Any, Dict, List, Optional, Tuple

import hnswlib
import numpy as np

from cns_py.vector.index import VectorIndex

logger = logging.getLogger(__name__)

class HnswVectorIndex(VectorIndex):
    """
    ANN backend using hnswlib.
    Provides approximate nearest neighbor search with HNSW.
    """
    def __init__(self, dim: int = 384, max_elements: int = 10000):
        self.dim = dim
        self.max_elements = max_elements
        self.count = 0
        
        # Hbwswlib index
        # Use 'ip' (Inner Product) with normalized vectors for Cosine Similarity.
        # This is often more numerically stable or standard for dense embeddings.
        self.algo = hnswlib.Index(space='ip', dim=dim)
        # Tuned for recall: M=48, ef_construction=800
        self.algo.init_index(max_elements=max_elements, ef_construction=800, M=48)
        
        # Map string IDs to integer IDs (hnswlib only supports int labels)
        self.id_map: Dict[str, int] = {}
        self.rev_id_map: Dict[int, str] = {}
        self.next_int_id = 0
        
        # Keep track of deleted int labels to reuse or filter
        self.deleted_ids: set[int] = set()
        
        # Metadata storage: int_id -> metadata
        self.metadata_store: Dict[str, Dict[str, Any]] = {}

    def upsert(self, doc_id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Insert or update a vector."""
        # Normalize
        vec = np.array(vector, dtype='float32')
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        else:
            # Zero vector handling
            vec = vec + 1e-10
            
        # Check if resizing needed
        if self.count >= self.max_elements:
             # Resize index
             new_max = self.max_elements * 2
             self.algo.resize_index(new_max)
             self.max_elements = new_max
        
        # Resolve ID
        if doc_id in self.id_map:
            int_id = self.id_map[doc_id]
        else:
            int_id = self.next_int_id
            self.next_int_id += 1
            self.id_map[doc_id] = int_id
            self.rev_id_map[int_id] = doc_id
        
        # Insert into HNSW
        self.algo.add_items([vec], [int_id])
        self.count += 1
        
        # Remove from deleted set if it was there (re-use case)
        if int_id in self.deleted_ids:
            self.deleted_ids.remove(int_id)
            
        if metadata:
            self.metadata_store[doc_id] = metadata

    def delete(self, doc_id: str) -> None:
        """Mark item as deleted."""
        if doc_id in self.id_map:
            int_id = self.id_map[doc_id]
            self.algo.mark_deleted(int_id)
            self.deleted_ids.add(int_id)
            # We don't remove from maps immediately to keep ID stable? 
            # Actually, we can just treat it as gone.
            # But hnswlib mark_deleted just excludes it from results.
            if doc_id in self.metadata_store:
                del self.metadata_store[doc_id]

    def query(self, vector: List[float], k: int = 10, filter: Optional[Dict[str, Any]] = None) -> List[Tuple[str, float]]:
        """
        Approximate search.
        """
        if self.count == 0 or len(self.id_map) == 0:
            return []
            
        # Normalize query
        vec = np.array(vector, dtype='float32')
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
            
        # HNSW query
        # Fetch more than k if filtering to account for post-filtering
        k_search = k
        if filter:
            k_search = k * 5 # heuristic, fetch more candidates
            
        k_search = min(k_search, self.count)
        if k_search <= 0:
            return []

        try:
            labels, distances = self.algo.knn_query(vec, k=k_search)
        except Exception:
            # Can happen if EF is too small or index empty
            return []
            
        results = []
        for int_id, dist in zip(labels[0], distances[0]):
            if int_id in self.deleted_ids:
                continue
                
            doc_id = self.rev_id_map.get(int_id)
            if not doc_id:
                continue
                
            # Filter check
            if filter:
                meta = self.metadata_store.get(doc_id)
                if not meta: 
                    continue # Filter provided but no metadata -> fail
                
                match = True
                for key, val in filter.items():
                    # Subset match (from Slice 3C spec)
                    if meta.get(key) != val:
                        match = False
                        break
                if not match:
                    continue
            
            # Convert distance to similarity
            # HNSW cosine distance is 1 - sim? 
            # HNSWlib: d = 1 - dot(A, B) for normalized vectors
            # So sim = 1 - d
            score = 1.0 - dist
            results.append((doc_id, float(score)))
            
        # Sort deterministic (Score DESC, Id ASC)
        # HNSW returns sorted by distance, but we re-sort for full determinism on ties
        results.sort(key=lambda x: (-x[1], x[0]))
        
        return results[:k]

    def bulk_load(self, items: List[Tuple[str, List[float], Dict[str, Any]]]) -> None:
        """Efficient bulk build."""
        count = len(items)
        if count == 0:
            return
            
        # Prepare data
        dim = len(items[0][1])
        # Re-init index for size
        self.algo = hnswlib.Index(space='ip', dim=dim)
        self.algo.init_index(max_elements=max(count, self.max_elements), ef_construction=800, M=48)
        
        data = []
        int_ids = []
        
        # Reset maps
        self.id_map = {}
        self.rev_id_map = {}
        self.next_int_id = 0
        self.metadata_store = {}
        
        for i, (doc_id, vec, meta) in enumerate(items):
            v_np = np.array(vec, dtype='float32')
            n = np.linalg.norm(v_np)
            if n > 0:
                v_np = v_np / n
            
            data.append(v_np)
            int_id = i
            int_ids.append(int_id)
            
            self.id_map[doc_id] = int_id
            self.rev_id_map[int_id] = doc_id
            if meta:
                self.metadata_store[doc_id] = meta
                
        self.algo.add_items(data, int_ids)
        self.next_int_id = count
        self.count = count
        self.max_elements = max(count, self.max_elements)

    def save(self, path: str) -> None:
        """Persist index and metadata."""
        # 1. Save HNSW index
        idx_path = f"{path}.hnsw"
        self.algo.save_index(idx_path)
        
        # 2. Save mappings and metadata
        meta_path = f"{path}.meta.pkl"
        state = {
            "id_map": self.id_map,
            "rev_id_map": self.rev_id_map,
            "next_int_id": self.next_int_id,
            "metadata_store": self.metadata_store,
            "max_elements": self.max_elements,
            "dim": self.dim
        }
        with open(meta_path, "wb") as f:
            pickle.dump(state, f)

    def load(self, path: str) -> None:
        """Load from disk."""
        idx_path = f"{path}.hnsw"
        meta_path = f"{path}.meta.pkl"
        
        if not os.path.exists(idx_path) or not os.path.exists(meta_path):
            raise FileNotFoundError("Index files missing")
            
        with open(meta_path, "rb") as f:
            state = pickle.load(f)
            
        self.id_map = state["id_map"]
        self.rev_id_map = state["rev_id_map"]
        self.next_int_id = state["next_int_id"]
        self.metadata_store = state["metadata_store"]
        self.max_elements = state["max_elements"]
        self.dim = state["dim"]
        
        self.algo = hnswlib.Index(space='ip', dim=self.dim)
        self.algo.load_index(idx_path, max_elements=self.max_elements)
        self.count = len(self.id_map)
