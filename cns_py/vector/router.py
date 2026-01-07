import re
from typing import List, Protocol, Tuple


class VectorRouter(Protocol):
    def route(self, text: str) -> List[Tuple[str, float]]:
        """Return list of (space_name, weight)."""
        ...


class HeuristicRouter:
    def route(self, text: str) -> List[Tuple[str, float]]:
        # Simple heuristics for code vs text
        # If it looks like Python, go to 'code', else 'default'
        if (
            re.search(r"^\s*(def |class |import |from |@|int |void |const )", text, re.MULTILINE)
            or ";" in text
        ):
            return [("code", 1.0)]
        return [("default", 1.0)]
