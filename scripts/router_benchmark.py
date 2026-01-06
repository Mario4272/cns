"""
Benchmark for Learned Routers (Slice 9.3).
Compares Single-Index vs Multi-Space+Router performance.
"""
import logging
import random
import time
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

from cns_py.vector import ExactInMemoryIndex
from cns_py.vector.embeddings import DeterministicStubProvider
from cns_py.vector.manager import IndexManager

# Suppress Logs
logging.basicConfig(level=logging.ERROR)

# Mock Rebuild globally to avoid DB access
IndexManager.rebuild = lambda self, space="default": None

# Configuration
NUM_DOCS_PER_DOMAIN = 50
NUM_QUERIES = 20
K = 10

@dataclass
class Document:
    id: str
    text: str
    domain: str # "code" or "text"
    vector: np.ndarray

def generate_dataset() -> Tuple[List[Document], List[Document]]:
    """Generate synthetic documents and queries."""
    provider = DeterministicStubProvider(dim=384)
    docs = []
    queries = []
    
    # Domain: Code
    for i in range(NUM_DOCS_PER_DOMAIN):
        # Generate pseudo-code
        keywords = ["def", "class", "import", "return", "var", "int", "str"]
        kw = random.choice(keywords)
        suffix = f"func_{i}"
        text = f"{kw} {suffix}()"
        vec = provider.embed_texts([text])[0]
        docs.append(Document(id=f"code_{i}", text=text, domain="code", vector=vec))
        
    # Domain: Text
    for i in range(NUM_DOCS_PER_DOMAIN):
        # Generate pseudo-text
        topics = ["apple", "history", "science", "politics", "art", "music"]
        topic = random.choice(topics)
        text = f"The {topic} of number {i}"
        vec = provider.embed_texts([text])[0]
        docs.append(Document(id=f"text_{i}", text=text, domain="default", vector=vec))
        
    # Queries (subset of docs to ensure ground truth exists)
    # Subset
    code_samples = [d for d in docs if d.domain == "code"]
    text_samples = [d for d in docs if d.domain == "default"]
    
    for _ in range(NUM_QUERIES // 2):
        target = random.choice(code_samples)
        queries.append(target)
        
    for _ in range(NUM_QUERIES // 2):
        target = random.choice(text_samples)
        queries.append(target)
        
    random.shuffle(docs)
    random.shuffle(queries)
    
    return docs, queries

def run_baseline(docs: List[Document], queries: List[Document]) -> float:
    """Run single-index baseline."""
    print("\n--- Baseline (Single Index: 'default') ---")
    mgr = IndexManager()
    mgr.indices["default"] = ExactInMemoryIndex()
    
    # Index all into default
    print(f"Indexing {len(docs)} documents into 'default'...")
    start_t = time.time()
    batch = [(d.id, d.vector, {"label": d.text}) for d in docs]
    mgr.indices["default"].bulk_load(batch)
    print(f"Indexing took {time.time() - start_t:.3f}s")
    
    # Query
    hits = 0
    latencies = []
    
    for q in queries:
        t0 = time.time()
        # Query default space explicitly logic (simulating dumb client)
        results = mgr.query(q.vector, k=K, space="default")
        lat = time.time() - t0
        latencies.append(lat)
        
        # Check recall (is q.id in results?)
        found_ids = [r[0] for r in results]
        if q.id in found_ids:
            hits += 1
            
    recall = hits / len(queries)
    if latencies:
        p95 = np.percentile(latencies, 95) * 1000
    else:
        p95 = 0.0
    print(f"Recall@{K}: {recall:.2f}")
    print(f"P95 Latency: {p95:.2f} ms")
    return recall

def run_multispace(docs: List[Document], queries: List[Document]) -> float:
    """Run multi-space with router."""
    print("\n--- Multi-Space (Router: 'auto') ---")
    mgr = IndexManager()
    mgr.startup() # inits default router
    
    # Create spaces
    mgr.indices["code"] = ExactInMemoryIndex()
    mgr.indices["default"] = ExactInMemoryIndex()
    
    # Index split
    code_docs = [d for d in docs if d.domain == "code"]
    text_docs = [d for d in docs if d.domain == "default"]
    
    print(f"Indexing {len(code_docs)} -> 'code', {len(text_docs)} -> 'default'...")
    
    mgr.indices["code"].bulk_load([(d.id, d.vector, {"label": d.text}) for d in code_docs])
    mgr.indices["default"].bulk_load([(d.id, d.vector, {"label": d.text}) for d in text_docs])
    
    # Query with auto
    hits = 0
    latencies = []
    router_hits = 0
    
    for q in queries:
        t0 = time.time()
        # Pass query_text for routing
        results = mgr.query(q.vector, k=K, space="auto", query_text=q.text)
        lat = time.time() - t0
        latencies.append(lat)
        
        # Check recall
        found_ids = [r[0] for r in results]
        if q.id in found_ids:
            hits += 1
            
        # Check router accuracy (did we query the right space?)
        # Implementation Detail: We can't easily spy on the router here without mocking.
        # But Recall is the proxy. If router sent "def foo" to "default", Recall would be 0 
        # (because "def foo" is ONLY in "code" index).
    
    recall = hits / len(queries)
    if latencies:
        p95 = np.percentile(latencies, 95) * 1000
    else:
        p95 = 0.0
    print(f"Recall@{K}: {recall:.2f}")
    print(f"P95 Latency: {p95:.2f} ms")
    return recall

def main():
    try:
        print("Generating Dataset...")
        docs, queries = generate_dataset()
        print(f"Docs: {len(docs)}, Queries: {len(queries)}")
        
        # 1. Baseline
        recall_base = run_baseline(docs, queries)
        
        # 2. Multi-Space
        recall_multi = run_multispace(docs, queries)
        
        report = []
        report.append("\n--- Summary ---")
        report.append(f"Baseline Recall: {recall_base:.2f}")
        report.append(f"Multi-Space Recall: {recall_multi:.2f}")
        
        diff = recall_multi - recall_base
        report.append(f"Diff: {diff:+.2f}")
        
        passed = False
        if diff >= -0.10: 
            report.append("PASS: Recall Maintained (within 10%)")
            passed = True
        else:
            report.append("FAIL: Recall Dropped significantly")
            
        with open("benchmark_results.txt", "w") as f:
            f.write("\n".join(report))
            
        for line in report:
            print(line)
            
        if not passed:
            exit(1)
            
    except Exception as e:
        import traceback
        with open("benchmark_error.txt", "w") as f:
            traceback.print_exc(file=f)
        print(f"CRITICAL ERROR: {e}")
        exit(1)

if __name__ == "__main__":
    main()
