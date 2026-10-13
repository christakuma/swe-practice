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


def clone_graph(node: Node | None, radius: int) -> Node | None:
    """Deep-copy the part of the graph within `radius` edges of `node`.

    Args:
        node: any node of a connected undirected graph, or None.
        radius: the largest number of edges a copied node may be from `node`,
            by its shortest route. Never negative.

    Returns:
        The copy of `node`. Each copy's neighbours are the copies of the
        original's neighbours that are within the radius, in the same order.
    """
    raise NotImplementedError
