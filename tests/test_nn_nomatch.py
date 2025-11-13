from __future__ import annotations

from cns_py.nn import nn_search


def test_nn_search_returns_empty_for_no_match():
    # Use a label that should not exist in the demo dataset
    ids = nn_search("__no_such_label__", k=5)
    assert isinstance(ids, list)
    assert len(ids) == 0
