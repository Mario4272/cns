"""
Vector Index Manager.
Handles lifecycle: loading, building, and updating the index.
"""
import logging
import os
import time
from typing import Any, Dict, List, Optional

from cns_py import config
from cns_py.storage.db import get_conn
from cns_py.vector import ExactInMemoryIndex, VectorIndex
from cns_py.vector.embeddings import DeterministicStubProvider, EmbeddingProvider
from cns_py.vector.router import HeuristicRouter, VectorRouter

logger = logging.getLogger(__name__)

class IndexManager:
    def __init__(self):
        self.enabled = config.vector_index_enabled()
        self.backend_type = config.vector_index_backend()
        self.path = config.vector_index_path()
        # Map space_name -> VectorIndex
        self.indices: Dict[str, VectorIndex] = {}
        
        # Provider could be configurable later. For Slice 5, default to Stub.
        # Ideally read from config "CNS_EMBEDDING_PROVIDER"
        self.provider: EmbeddingProvider = DeterministicStubProvider(dim=384)
        self.dim = self.provider.dimension
        
        # Router for "auto" queries
        self.router: VectorRouter = HeuristicRouter()

    def _get_space_path(self, space: str) -> str:
        """Generate storage path prefix for a named space."""
        # E.g. data/vector_index_default
        return f"{self.path}_{space}"

    def _create_index_instance(self) -> VectorIndex:
        """Factory to create a new, empty index instance based on config."""
        if self.backend_type == "pg":
            from cns_py.vector import PgVectorIndex
            return PgVectorIndex(dim=self.dim)
        elif self.backend_type == "ann":
             try:
                 from cns_py.vector.hnsw_index import HnswVectorIndex
                 return HnswVectorIndex(dim=self.dim)
             except ImportError:
                 logger.error(
                     "HNSW backend requested but hnswlib not available. Falling back to memory."
                 )
                 return ExactInMemoryIndex()
        else:
            return ExactInMemoryIndex()

    def _load_or_create_space(self, space: str) -> None:
        """Initialize a space, loading from disk if available."""
        if space in self.indices:
            return

        index = self._create_index_instance()
        space_path = self._get_space_path(space)

        # Persistence loading logic
        loaded = False
        if self.backend_type == "ann":
             if os.path.exists(f"{space_path}.hnsw"):
                 logger.info(
                     f"Loading persisted HNSW index for space '{space}' from {space_path}..."
                 )
                 # HnswVectorIndex.load expects the prefix
                 index.load(space_path)
                 loaded = True
        elif self.backend_type == "memory":
            if os.path.exists(f"{space_path}.npz"):
                logger.info(
                    f"Loading persisted memory index for space '{space}' from {space_path}..."
                )
                try:
                    index.load(space_path)
                    logger.info(f"Space '{space}' loaded successfully.")
                    loaded = True
                except Exception as e:
                    logger.error(f"Failed to load space '{space}': {e}. Creating new.")
        
        self.indices[space] = index
        return loaded

    def startup(self) -> None:
        """Initialize the default index space."""
        # Refresh config
        self.enabled = config.vector_index_enabled()
        self.backend_type = config.vector_index_backend()
        self.path = config.vector_index_path()
        
        if not self.enabled:
            logger.info("Vector index disabled.")
            return

        logger.info(f"Initializing Vector Manager ({self.backend_type})...")
        
        # Always init default space
        loaded = self._load_or_create_space("default")
        
        # If default wasn't loaded from disk, rebuild it from DB
        if not loaded:
            self.rebuild(space="default")
        
    def shutdown(self) -> None:
        """Persist all spaces on shutdown."""
        if not self.enabled:
            return
            
        # Support saving for both memory and ann backends
        if self.backend_type in ["memory", "ann"]:
            for space, index in self.indices.items():
                space_path = self._get_space_path(space)
                logger.info(f"Persisting space '{space}' to {space_path}...")
                # Ensure parent dir exists
                os.makedirs(os.path.dirname(os.path.abspath(space_path)), exist_ok=True)
                index.save(space_path)

    def rebuild(self, space: str = "default") -> None:
        """Full rebuild of a specific space from DB atoms."""
        # Ensure space exists
        if space not in self.indices:
            self.indices[space] = self._create_index_instance()
            
        index = self.indices[space]
            
        logger.info(f"Rebuilding space '{space}' from source atoms...")
        start_t = time.time()
        
        # TODO: In Phase 9.1, we don't have a 'space' column in DB yet.
        # So we only rebuild 'default' space with ALL atoms? 
        # Or should we just filter nothing for now?
        # Implementing basic fetch.
        
        with get_conn() as conn:
            with conn.cursor() as cur:
                # TODO: Filter by space once DB supports it
                cur.execute(
                    "SELECT id, label, text, kind FROM atoms "
                    "WHERE kind IN ('Entity', 'Concept')"
                )
                rows = cur.fetchall()
                
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
            logger.warning(f"No content found for space '{space}'.")
            return
            
        # Batch embed
        vecs = self.provider.embed_texts(texts)
        
        # Assemble for bulk load
        bulk_items = []
        for doc_id, vec, meta in zip(doc_ids, vecs, metas):
            bulk_items.append((doc_id, vec, meta))
            
        index.bulk_load(bulk_items)
            
        duration = time.time() - start_t
        logger.info(
            f"Rebuild '{space}' complete. Indexed {len(bulk_items)} items in {duration:.3f}s."
        )

    def reindex(self) -> None:
        """Public alias for rebuild default."""
        self.rebuild("default")

    def query(
        self,
        query_vec: Any,
        k: int,
        filter: Optional[Dict] = None,
        space: str = "default",
        query_text: Optional[str] = None
    ) -> List[Any]:
        """
        Query a specific space or use 'auto' to route.
        query_text is optional, but required for 'auto' routing logic. 
        (If not provided, auto falls back to default).
        """
        if space == "auto":
            return self._query_auto(query_vec, k, query_text, filter=filter)
            
        if space not in self.indices:
            # Auto-initialize? Or return empty?
            # For now, if requested space doesn't exist, return empty.
            # In future (Slice 9.2), we might auto-load.
            return []
            
        return self.indices[space].query(query_vec, k, filter=filter)

    def _query_auto(
        self,
        query_vec: Any,
        k: int,
        query_text: Optional[str] = None,
        filter: Optional[Dict] = None
    ) -> List[Any]:
        """
        Route query to multiple spaces and merge results.
        """
        if not query_text:
            # Fallback if no text text available for routing
            return self.query(query_vec, k, filter=filter, space="default")
            
        # 1. Get targets
        targets = self.router.route(query_text) # List[Tuple[space, weight]]
        
        # 2. Query each space
        all_results = []
        for space, weight in targets:
            if space not in self.indices:
                # Try loading it if persisted?
                # For now assume explicit rebuilds or load.
                # Just skip if missing to avoid errors.
                continue
                
            # Query space
            space_results = self.indices[space].query(query_vec, k, filter=filter)
            # Apply weight to scores
            # Result is (doc_id, score)
            for doc_id, score in space_results:
                weighted_score = score * weight
                all_results.append((doc_id, weighted_score))
                
        # 3. Merge & Deduplicate
        # If same doc_id comes from multiple spaces (rare but possible if shared ID space),
        # take max score? Or sum?
        # Assuming ID uniqueness mostly, or max score wins.
        best_scores: Dict[str, float] = {}
        for doc_id, score in all_results:
            if doc_id not in best_scores or score > best_scores[doc_id]:
                best_scores[doc_id] = score
                
        # 4. Sort & Top K
        # Sort desc by score
        merged = sorted(best_scores.items(), key=lambda x: x[1], reverse=True)
        return merged[:k]

    def get_index(self, space: str = "default") -> Optional[VectorIndex]:
        """Direct access to index instance (for testing/debug)."""
        return self.indices.get(space)

    def get_status(self) -> Dict[str, Any]:
        """Return operational status of the index subsystem."""
        spaces_stat = {}
        for name, idx in self.indices.items():
            # Try to get count
            count = "unknown"
            if hasattr(idx, "ids"): # Memory index
                 count = len(idx.ids)
            spaces_stat[name] = {
                "type": type(idx).__name__,
                "count": count
            }
            
        return {
            "enabled": self.enabled,
            "backend": self.backend_type,
            "root_path": self.path,
            "provider_dim": self.dim,
            "spaces": spaces_stat
        }
