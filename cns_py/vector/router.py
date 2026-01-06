import re
from typing import Protocol


class VectorRouter(Protocol):
    def route(self, text: str) -> str:
        """Return the target space name for the given text."""
        ...

class HeuristicRouter:
    def route(self, text: str) -> str:
        # Simple heuristics for code vs text
        # If it looks like Python, go to 'code', else 'default'
        if re.search(r'^\s*(def |class |import |from |@)', text, re.MULTILINE):
            return "code"
        return "default"
