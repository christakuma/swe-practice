"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class Node:
    """An undirected graph node holding a value and its neighbours."""

    def __init__(self, value: int, neighbours: list[Node] | None = None) -> None:
        self.value = value
        self.neighbours: list[Node] = neighbours if neighbours is not None else []


def clone_graph(node: Node | None) -> Node | None:
    """Deep-copy the graph reachable from `node`.

    A graph is a tree plus cycles, and the cycles are the entire problem. A
    plain recursion into every neighbour does not terminate: node 1 copies
    node 2, which copies node 1, forever. Every undirected edge is already a
    cycle, since it appears in both nodes' neighbour lists -- so this is not an
    edge case, it is the first case.

    `copies` solves it, and the tidy observation is that **it is doing two jobs
    with one structure**. It is the visited set -- "have I handled this node?"
    -- and it is the lookup used to wire edges -- "what is this original's
    copy?". A separate `visited` set alongside it would be the same
    information twice.

    **The new node must go into the map before recursing.** Insert it
    afterwards and a cycle coming back around finds nothing, recurses again,
    and the recursion never bottoms out. This is the same ordering obligation
    as marking a cell before descending in `find-a-word-in-a-grid`, with one
    difference worth noticing: there the mark was *undone* on the way out,
    because it meant "on the current path". Here it is permanent, because it
    means "already copied". Two superficially identical bookkeeping steps with
    opposite lifetimes -- and picking the wrong one gives either an infinite
    loop or a search that blocks itself.

    O(V + E): each node is copied once and each edge is followed once from each
    end. O(V) for the map plus the recursion depth.
    """
    copies: dict[int, Node] = {}

    def copy(original: Node) -> Node:
        existing = copies.get(id(original))
        if existing is not None:
            return existing
        duplicate = Node(original.value)
        copies[id(original)] = duplicate
        # Only now, with the copy registered, is it safe to follow the edges.
        duplicate.neighbours = [copy(neighbour) for neighbour in original.neighbours]
        return duplicate

    return None if node is None else copy(node)
