from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class CqlQuery:
    label: Optional[str] = None
    predicate: Optional[str] = None
    asof_iso: Optional[str] = None
    belief_ge: Optional[float] = None
    explain: bool = True
    provenance: bool = True


def parse(query: str) -> CqlQuery:
    """
    Minimal parser for queries like:
    MATCH label="FrameworkX" PREDICATE supports_tls ASOF 2025-01-01T00:00:00Z BELIEF >= 0.7 RETURN EXPLAIN PROVENANCE

    All keywords are optional; defaults:
      - explain: True
      - provenance: True
    """
    tokens = query.strip().replace("\n", " ").split()
    i = 0
    out = CqlQuery()

    while i < len(tokens):
        tok = tokens[i].upper()
        if tok == "MATCH":
            i += 1
            continue
        if tok.startswith("LABEL"):
            # LABEL or label="..."
            if "=" in tokens[i]:
                k, v = tokens[i].split("=", 1)
                out.label = v.strip().strip('"')
                i += 1
            else:
                # LABEL <value>
                if i + 1 < len(tokens):
                    out.label = tokens[i + 1].strip('"')
                    i += 2
                else:
                    i += 1
            continue
        if tok == "PREDICATE":
            if i + 1 < len(tokens):
                out.predicate = tokens[i + 1]
                i += 2
            else:
                i += 1
            continue
        if tok == "ASOF":
            if i + 1 < len(tokens):
                out.asof_iso = tokens[i + 1]
                i += 2
            else:
                i += 1
            continue
        if tok == "BELIEF":
            # BELIEF >= 0.7
            if i + 2 < len(tokens) and tokens[i + 1] in {">=", ">"}:
                try:
                    out.belief_ge = float(tokens[i + 2])
                except ValueError:
                    pass
                i += 3
            else:
                i += 1
            continue
        if tok == "RETURN":
            i += 1
            continue
        if tok == "EXPLAIN":
            out.explain = True
            i += 1
            continue
        if tok == "PROVENANCE":
            out.provenance = True
            i += 1
            continue
        # Unrecognized token; skip
        i += 1

    return out
