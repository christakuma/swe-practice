"""Your solution goes here.

The tests import both `Node` and `clone_graph` from this module, so keep the
class as it is -- it is how the tests build graphs to hand you.
"""

from __future__ import annotations


class Node:
    """An undirected graph node holding a value and its neighbours."""

    def __init__(self, value: int, neighbours: list[Node] | None = None) -> None:
        self.value = value
        self.neighbours: list[Node] = neighbours if neighbours is not None else []


def clone_graph(node: Node | None) -> Node | None:
    """Deep-copy the graph reachable from `node`.

    Args:
        node: any node of a connected undirected graph, or None.

    Returns:
        The copy of `node`. Every node and every neighbour reference in the
        result is newly created; none is shared with the input.
    """
    raise NotImplementedError
