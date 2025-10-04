from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Provenance:
    source_id: Optional[str] = None
    uri: Optional[str] = None
    line_span: Optional[str] = None
    fetched_at: Optional[str] = None
    hash: Optional[str] = None


@dataclass
class ExplainStep:
    name: str
    ms: float
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExplainReport:
    steps: List[ExplainStep]
    total_ms: float


@dataclass
class ResultItem:
    subject_label: str
    predicate: Optional[str]
    object_label: str
    confidence: Optional[float]
    provenance: List[Provenance] = field(default_factory=list)
    # Optional belief details for EXPLAIN
    belief_details: Optional[Dict[str, Any]] = None
