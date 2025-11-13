from __future__ import annotations

from typing import List

from cns_py.nn import nn_search


def test_nn_search_respects_k_and_types():
    ids: List[int] = nn_search("FrameworkX", k=2)
    assert 0 < len(ids) <= 2
    assert all(isinstance(i, int) for i in ids)


def test_nn_search_case_insensitive_matches():
    ids_upper = nn_search("FrameworkX", k=5)
    ids_lower = nn_search("frameworkx", k=5)
    # Both queries should return at least one id and have overlap
    assert len(ids_upper) >= 1 and len(ids_lower) >= 1
    assert set(ids_upper).intersection(ids_lower)
