"""
Unit tests for HeuristicRouter (Slice 9.2).
"""
from cns_py.vector.router import HeuristicRouter


def test_heuristic_router_defaults():
    router = HeuristicRouter()
    
    # Generic query
    routes = router.route("hello world")
    assert len(routes) == 1
    assert routes[0] == ("default", 1.0)
    
    # Physics/Concepts
    routes = router.route("quantum mechanics")
    assert len(routes) == 1
    assert routes[0] == ("default", 1.0)

def test_heuristic_router_code_detection():
    router = HeuristicRouter()
    
    # Python def
    routes = router.route("def functionality():")
    spaces = {r[0]: r[1] for r in routes}
    assert "code" in spaces
    assert spaces["code"] > 0.5
    
    # Class
    routes = router.route("class MyClass")
    spaces = {r[0]: r[1] for r in routes}
    assert "code" in spaces
    
    # Import
    routes = router.route("import sys")
    spaces = {r[0]: r[1] for r in routes}
    assert "code" in spaces
    
    # C-style (weak signal, but handled)
    routes = router.route("int x = 5;")
    spaces = {r[0]: r[1] for r in routes}
    assert "code" in spaces
