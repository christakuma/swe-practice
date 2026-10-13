"""Reference solution. CI asserts this passes every test in `tests.py`."""

from __future__ import annotations


class Node:
    """An undirected graph node holding a value and its neighbours."""

    def __init__(self, value: int, neighbours: list[Node] | None = None) -> None:
        self.value = value
        self.neighbours: list[Node] = neighbours if neighbours is not None else []


def clone_graph(node: Node | None, radius: int) -> Node | None:
    """Deep-copy the part of the graph within `radius` edges of `node`.

    Breadth-first, one whole layer per round, because the question is about
    shortest distances and that is the order in which breadth-first search
    meets nodes. `originals` collects every node within the radius, each one
    added at the round equal to its distance; `copies` is the same map the
    full clone uses, from an original to its duplicate.

    The edges are wired afterwards, in a second pass, and that is what makes
    the membership test trivial: by then `copies` is complete, so "is this
    neighbour within the radius?" is "does it have a copy?". Wiring during
    the search would have to guess about nodes it has not reached yet.
    """
    if node is None:
        return None
    copies: dict[int, Node] = {id(node): Node(node.value)}
    originals = [node]
    layer = [node]
    for _ in range(radius):
        following = []
        for original in layer:
            for neighbour in original.neighbours:
                if id(neighbour) not in copies:
                    copies[id(neighbour)] = Node(neighbour.value)
                    following.append(neighbour)
        originals.extend(following)
        layer = following

    for original in originals:
        copies[id(original)].neighbours = [
            copies[id(neighbour)]
            for neighbour in original.neighbours
            if id(neighbour) in copies
        ]
    return copies[id(node)]
