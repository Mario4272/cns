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

from cns_py.vector.embeddings import EmbeddingProvider, DeterministicStubProvider

logger = logging.getLogger(__name__)

class IndexManager:
    def __init__(self):
        self.enabled = config.vector_index_enabled()
        self.backend_type = config.vector_index_backend()
        self.path = config.vector_index_path()
        self.index: Optional[VectorIndex] = None
        
        # Provider could be configurable later. For Slice 5, default to Stub.
        # Ideally read from config "CNS_EMBEDDING_PROVIDER"
        self.provider: EmbeddingProvider = DeterministicStubProvider(dim=384)
        self.dim = self.provider.dimension

    def startup(self) -> None:
        """Initialize the index, load from disk if avail, else rebuild."""
        # Refresh config
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
                return
        elif self.backend_type == "ann": # Slice 5A support
             try:
                 from cns_py.vector.hnsw_index import HnswVectorIndex
                 # For HNSW persistence we might need separate path handling
                 self.index = HnswVectorIndex(dim=self.dim)
                 if os.path.exists(f"{self.path}.hnsw"):
                     logger.info(f"Loading persisted HNSW index from {self.path}...")
                     self.index.load(self.path)
                     return
             except ImportError:
                 logger.error("HNSW backend requested but hnswlib not available.")
                 # Fallback to memory?
                 self.index = ExactInMemoryIndex()
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
            
        # Support saving for both memory and ann backends
        # Pg doesn't need shutdown save
        if self.backend_type in ["memory", "ann"]:
            logger.info(f"Persisting index to {self.path}...")
            os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
            self.index.save(self.path)

    def rebuild(self) -> None:
        """Full rebuild from DB atoms."""
        if not self.index:
            return
            
        logger.info("Rebuilding vector index from source atoms...")
        start_t = time.time()
        
        items = []
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, label, text, kind FROM atoms "
                    "WHERE kind IN ('Entity', 'Concept')"
                )
                rows = cur.fetchall()
                
        # Batch processing? For now simple list
        # Extract Texts
        texts = []
        doc_ids = []
        metas = []
        
        for row in rows:
            atom_id_int, label, text, kind = row
            # Content Rule: Text if present, else label
            content = text if text and text.strip() else label
            if not content:
                continue
                
            texts.append(content)
            doc_ids.append(str(atom_id_int))
            metas.append({"kind": kind, "label": label})
            
        if not texts:
            return
            
        # Batch embed
        # TODO: chunk if too large
        vecs = self.provider.embed_texts(texts)
        
        # Assemble for bulk load
        bulk_items = []
        for doc_id, vec, meta in zip(doc_ids, vecs, metas):
            bulk_items.append((doc_id, vec, meta))
            
        self.index.bulk_load(bulk_items)
            
        duration = time.time() - start_t
        logger.info(f"Index rebuild complete. Indexed {len(items)} items in {duration:.3f}s.")

    def reindex(self) -> None:
        """Public alias for rebuild, could be exposed to CLI or API."""
        self.rebuild()

    def query(self, *args, **kwargs):
        """Proxy to index.query"""
        if self.index:
            return self.index.query(*args, **kwargs)
        return []
