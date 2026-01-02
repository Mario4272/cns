"""
Vector Index Manager.
Handles lifecycle: loading, building, and updating the index.
"""
import logging
import os
import time
from typing import List, Optional, Any, Dict
import numpy as np

from cns_py import config
from cns_py.vector import VectorIndex, ExactInMemoryIndex, PgVectorIndex
from cns_py.storage.db import get_conn

logger = logging.getLogger(__name__)

class IndexManager:
    def __init__(self):
        self.enabled = config.vector_index_enabled()
        self.backend_type = config.vector_index_backend()
        self.path = config.vector_index_path()
        self.index: Optional[VectorIndex] = None
        
        # Determine embedding dimension (fixed for dummy embedding)
        self.dim = 384 

    def startup(self) -> None:
        """Initialize the index, load from disk if avail, else rebuild."""
        # Refresh config to pick up env vars set after init (e.g. tests)
        self.enabled = config.vector_index_enabled()
        self.backend_type = config.vector_index_backend()
        self.path = config.vector_index_path()

        if not self.enabled:
            logger.info("Vector index disabled.")
            return

        logger.info(f"Initializing Vector Index ({self.backend_type})...")
        
        if self.backend_type == "pg":
            try:
                self.index = PgVectorIndex(dim=self.dim)
            except Exception as e:
                logger.error(f"Failed to init PgVectorIndex: {e}")
                # Fallback? Or fail? Instructions say "swappable". Let's fail safe to Valid State (None)
                return
        else:
            self.index = ExactInMemoryIndex()
            # Try to load persistence
            if os.path.exists(f"{self.path}.npz"):
                logger.info(f"Loading persisted index from {self.path}...")
                try:
                    self.index.load(self.path)
                    logger.info("Index loaded successfully.")
                    return # Loaded, no need to rebuild
                except Exception as e:
                    logger.error(f"Failed to load index: {e}. Rebuilding...")
            
        # Rebuild if not loaded
        self.rebuild()
        
    def shutdown(self) -> None:
        """Persist state on shutdown."""
        if not self.index or not self.enabled:
            return
            
        if self.backend_type == "memory":
            logger.info(f"Persisting index to {self.path}...")
            # Ensure dir exists
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
            self.index.save(self.path)

    def rebuild(self) -> None:
        """Full rebuild from DB atoms."""
        if not self.index:
            return
            
        logger.info("Rebuilding vector index from source atoms...")
        start_t = time.time()
        
        # 1. Fetch relevant atoms (Entity, Concept)
        # TODO: Paging for large DBs. Slice 4 assumes small/medium fit in memory bulk load.
        items = []
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, label, text, kind FROM atoms "
                    "WHERE kind IN ('Entity', 'Concept')"
                )
                for row in cur.fetchall():
                    atom_id_int, label, text, kind = row
                    
                    # Content to embed: Prefer text, fall back to label
                    content = text if text and text.strip() else label
                    if not content:
                        continue
                        
                    vec = self._embed(content)
                    
                    # Metadata for filtering
                    meta = {
                        "kind": kind,
                        "label": label
                    }
                    items.append((str(atom_id_int), vec, meta))
        
        # 2. Bulk load
        if items:
            self.index.bulk_load(items)
            
        duration = time.time() - start_t
        logger.info(f"Index rebuild complete. Indexed {len(items)} items in {duration:.3f}s.")

    def _embed(self, text: str) -> List[float]:
        """
        Deterministic dummy embedding for Slice 4.
        Projects text string to a fixed-size vector (dim=384).
        Uses simple hashing to be deterministic and dependency-free.
        """
        # Seed generator with hash of text for repeatability
        import hashlib
        h = hashlib.md5(text.encode("utf8")).hexdigest()
        seed = int(h[:8], 16) # Use first 8 hex chars as seed
        
        rng = np.random.RandomState(seed)
        # Generate random vector
        vec = rng.randn(self.dim)
        # Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()
        
    def query(self, *args, **kwargs):
        """Proxy to index.query"""
        if self.index:
            return self.index.query(*args, **kwargs)
        return []
