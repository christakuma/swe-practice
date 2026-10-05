"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from __future__ import annotations

from solution import Node, clone_graph


def build(edges: dict[int, list[int]]) -> dict[int, Node]:
    """Build an undirected graph from an adjacency map."""
    nodes = {value: Node(value) for value in edges}
    for value, neighbours in edges.items():
        nodes[value].neighbours = [nodes[other] for other in neighbours]
    return nodes


def fingerprint(start: Node | None) -> dict[int, list[int]]:
    """The adjacency map reachable from `start`, by value."""
    if start is None:
        return {}
    out: dict[int, list[int]] = {}
    stack = [start]
    while stack:
        node = stack.pop()
        if node.value in out:
            continue
        out[node.value] = sorted(n.value for n in node.neighbours)
        stack.extend(node.neighbours)
    return out


def reachable(start: Node | None) -> list[Node]:
    """Every node reachable from `start`, by identity."""
    if start is None:
        return []
    seen: dict[int, Node] = {}
    stack = [start]
    while stack:
        node = stack.pop()
        if id(node) in seen:
            continue
        seen[id(node)] = node
        stack.extend(node.neighbours)
    return list(seen.values())


SQUARE = {1: [2, 4], 2: [1, 3], 3: [2, 4], 4: [1, 3]}


def test_copies_the_shape() -> None:
    """Produces a graph with the same values and edges."""
    nodes = build(SQUARE)

    copy = clone_graph(nodes[1])

    assert fingerprint(copy) == fingerprint(nodes[1])


def test_handles_an_empty_graph() -> None:
    """Returns None for None."""
    assert clone_graph(None) is None


def test_handles_a_single_node_with_no_edges() -> None:
    """Copies an isolated node."""
    original = Node(1)

    copy = clone_graph(original)

    assert copy is not None
    assert copy is not original
    assert copy.value == 1
    assert copy.neighbours == []


def test_terminates_on_a_two_node_cycle() -> None:
    """Copies a pair of mutually adjacent nodes without recursing forever.

    An undirected edge is already a cycle: node 1 lists node 2 and node 2
    lists node 1. A recursion without a registry of copies never bottoms out
    here, which is the first case rather than an edge case.
    """
    nodes = build({1: [2], 2: [1]})

    copy = clone_graph(nodes[1])

    assert fingerprint(copy) == {1: [2], 2: [1]}


def test_handles_a_self_loop() -> None:
    """Copies a node that is its own neighbour.

    Registering the copy only *after* recursing fails here immediately -- the
    node's own neighbour list contains itself, so the lookup must already
    succeed mid-construction.
    """
    original = Node(1)
    original.neighbours = [original]

    copy = clone_graph(original)

    assert copy is not None
    assert copy is not original
    assert copy.neighbours == [copy]


def test_shares_no_nodes_with_the_original() -> None:
    """Creates every node fresh.

    The point of a deep copy. A solution returning the original, or wiring new
    nodes to old neighbours, passes every shape check above.
    """
    nodes = build(SQUARE)

    copy = clone_graph(nodes[1])

    originals = {id(node) for node in reachable(nodes[1])}
    duplicates = {id(node) for node in reachable(copy)}

    assert len(duplicates) == 4
    assert originals.isdisjoint(duplicates)


def test_copies_each_node_exactly_once() -> None:
    """Does not duplicate a node reached by two different paths.

    In the square, node 3 is reachable from node 1 via 2 and via 4. Without a
    registry the two routes build two separate copies of it, so the copy has
    more nodes than the original and its edges disagree.
    """
    nodes = build(SQUARE)

    copy = clone_graph(nodes[1])

    assert len(reachable(copy)) == 4


def test_preserves_mutual_adjacency() -> None:
    """Keeps edges undirected in the copy.

    If A lists B in the copy, B must list A -- and both must be copies. A
    solution that rebuilds neighbour lists from values rather than from the
    registry can produce a one-way edge.
    """
    nodes = build(SQUARE)

    copy = clone_graph(nodes[1])
    assert copy is not None

    for node in reachable(copy):
        for neighbour in node.neighbours:
            assert node in neighbour.neighbours, (node.value, neighbour.value)


def test_does_not_mutate_the_original() -> None:
    """Leaves the input graph untouched."""
    nodes = build(SQUARE)
    before = fingerprint(nodes[1])
    originals = {id(node) for node in reachable(nodes[1])}

    clone_graph(nodes[1])

    assert fingerprint(nodes[1]) == before
    assert {id(node) for node in reachable(nodes[1])} == originals


def test_handles_duplicate_values() -> None:
    """Distinguishes nodes by identity, not by value.

    Two distinct nodes may hold the same value, so a registry keyed on the
    value merges them.
    """
    first = Node(7)
    second = Node(7)
    third = Node(9)
    first.neighbours = [second, third]
    second.neighbours = [first]
    third.neighbours = [first]

    copy = clone_graph(first)
    assert copy is not None

    assert len(reachable(copy)) == 3
    assert sorted(n.value for n in copy.neighbours) == [7, 9]


def test_handles_a_long_chain() -> None:
    """Copies a chain long enough to matter."""
    chain = [Node(value) for value in range(300)]
    for index, node in enumerate(chain):
        if index > 0:
            node.neighbours.append(chain[index - 1])
        if index + 1 < len(chain):
            node.neighbours.append(chain[index + 1])

    copy = clone_graph(chain[0])

    assert len(reachable(copy)) == 300
    assert fingerprint(copy) == fingerprint(chain[0])


def test_handles_a_dense_graph() -> None:
    """Copies a graph where every node is adjacent to every other."""
    size = 60
    nodes = [Node(value) for value in range(size)]
    for node in nodes:
        node.neighbours = [other for other in nodes if other is not node]

    copy = clone_graph(nodes[0])

    assert len(reachable(copy)) == size
    assert fingerprint(copy) == fingerprint(nodes[0])
    assert {id(n) for n in reachable(copy)}.isdisjoint({id(n) for n in nodes})
