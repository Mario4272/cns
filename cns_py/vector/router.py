"""
Vector Router Module.
Determines which vector space(s) to query based on input text.
"""
import re
from typing import List, Protocol, Tuple, Dict

class VectorRouter(Protocol):
    """Interface for routing queries to vector spaces."""
    def route(self, query_text: str) -> List[Tuple[str, float]]:
        """
        Return a list of (space_name, weight) tuples.
        Weights should ideally sum to 1.0, or at least be relative importance.
        """
        ...

class HeuristicRouter:
    """
    Simple rule-based router.
    Detects patterns (e.g., code syntax) to prefer specific spaces.
    """
    def __init__(self):
        # Regex patterns for code detection
        self.code_patterns = [
            re.compile(r"def\s+\w+"),       # Python def
            re.compile(r"class\s+\w+"),     # Class def
            re.compile(r"import\s+\w+"),    # Import
            re.compile(r"return\s+"),       # Return
            re.compile(r"(var|let|const)\s+\w+"), # JS style
            re.compile(r"(int|float|str|bool)\s+\w+"), # Typed langs
            re.compile(r"[{};=]"),          # C-style syntax chars (weak signal)
        ]
    
    def route(self, query_text: str) -> List[Tuple[str, float]]:
        # Default strategy: Mostly "default", unless strong signal
        
        # 1. Code Detection
        is_code = False
        for pat in self.code_patterns:
            if pat.search(query_text):
                is_code = True
                break
        
        if is_code:
            # Strong preference for code space, but keep default for fallback?
            # For v0, let's be expansive.
            return [("code", 0.8), ("default", 0.2)]
            
        # 2. Tech Terms (concept -> tech space?) - Future
        
        # Fallback
        return [("default", 1.0)]
