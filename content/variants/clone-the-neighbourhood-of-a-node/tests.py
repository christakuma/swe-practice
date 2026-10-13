"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations

from solution import Node, clone_graph


def graph(size: int, edges: list[tuple[int, int]]) -> list[Node]:
    """`size` nodes valued by index, joined by undirected edges in order."""
    nodes = [Node(index) for index in range(size)]
    for first, second in edges:
        nodes[first].neighbours.append(nodes[second])
        if first != second:
            nodes[second].neighbours.append(nodes[first])
    return nodes


def expected(start: Node, radius: int) -> dict[int, list[int]]:
    """Value -> neighbour values of the wanted copy, for distinct values."""
    distance = {start.value: 0}
    queue = [start]
    for node in queue:
        for neighbour in node.neighbours:
            if neighbour.value not in distance:
                distance[neighbour.value] = distance[node.value] + 1
                queue.append(neighbour)
    return {
        node.value: [n.value for n in node.neighbours if distance[n.value] <= radius]
        for node in queue
        if distance[node.value] <= radius
    }


def describe(copy: Node, originals: list[Node]) -> dict[int, list[int]]:
    """Value -> neighbour values of a returned copy, checking it as it goes."""
    forbidden = {id(node) for node in originals}
    seen: dict[int, Node] = {}
    stack = [copy]
    while stack:
        node = stack.pop()
        assert id(node) not in forbidden, "the copy contains an original node"
        if node.value in seen:
            assert seen[node.value] is node, "one original was copied twice"
            continue
        seen[node.value] = node
        stack.extend(node.neighbours)
    return {value: [n.value for n in node.neighbours] for value, node in seen.items()}


TRIANGLE_WITH_A_TAIL = [(0, 1), (0, 2), (1, 2), (2, 3)]


def test_copies_everything_when_the_radius_is_large() -> None:
    """Copies the whole graph when every node is within the radius."""
    nodes = graph(4, TRIANGLE_WITH_A_TAIL)

    copy = clone_graph(nodes[0], 10)

    assert copy is not None
    assert describe(copy, nodes) == expected(nodes[0], 10)
    assert len(describe(copy, nodes)) == 4


def test_a_radius_of_zero_is_the_node_alone() -> None:
    """Copies only the starting node, with no neighbours, for a radius of 0."""
    nodes = graph(3, [(0, 1), (1, 2)])

    copy = clone_graph(nodes[1], 0)

    assert copy is not None
    assert copy is not nodes[1]
    assert (copy.value, copy.neighbours) == (1, [])


def test_drops_edges_that_leave_the_radius() -> None:
    """Leaves out a node beyond the radius and the edge that led to it."""
    nodes = graph(4, [(0, 1), (1, 2), (2, 3)])

    copy = clone_graph(nodes[0], 2)

    assert copy is not None
    assert describe(copy, nodes) == {0: [1], 1: [0, 2], 2: [1]}


def test_measures_distance_by_the_shortest_route() -> None:
    """Includes a node that is in range by one route and out of range by another.

    A triangle 0, 1, 2 with 3 hanging off 2, copied from 0 with radius 2. A
    depth-first walk goes 0, 1, 2 and arrives at 2 with its budget spent, so
    it never looks at 3 -- which is two edges from 0 by way of the direct edge.
    """
    nodes = graph(4, TRIANGLE_WITH_A_TAIL)

    copy = clone_graph(nodes[0], 2)

    assert copy is not None
    assert describe(copy, nodes) == {0: [1, 2], 1: [0, 2], 2: [0, 1, 3], 3: [2]}


def test_keeps_an_edge_between_two_nodes_on_the_rim() -> None:
    """Keeps the edge joining two nodes that are both exactly at the radius."""
    nodes = graph(3, [(0, 1), (0, 2), (1, 2)])

    copy = clone_graph(nodes[0], 1)

    assert copy is not None
    assert describe(copy, nodes) == {0: [1, 2], 1: [0, 2], 2: [0, 1]}


def test_keeps_a_node_that_is_its_own_neighbour() -> None:
    """Copies a self-loop as an edge from the copy to itself."""
    nodes = graph(2, [(0, 0), (0, 1)])

    copy = clone_graph(nodes[0], 0)

    assert copy is not None
    assert copy.neighbours == [copy]


def test_returns_none_for_no_graph() -> None:
    """Returns None for an empty graph, whatever the radius."""
    assert clone_graph(None, 0) is None
    assert clone_graph(None, 5) is None


def test_agrees_with_measured_distances_on_every_small_graph() -> None:
    """Matches a breadth-first measurement for every graph of four nodes.

    Every set of edges on four nodes, from every starting node, at every
    radius from 0 to 3. Neighbour order is compared as well as membership.
    """
    pairs = list(combinations(range(4), 2))
    for chosen in range(2 ** len(pairs)):
        edges = [pair for bit, pair in enumerate(pairs) if chosen >> bit & 1]
        for start in range(4):
            for radius in range(4):
                nodes = graph(4, edges)
                copy = clone_graph(nodes[start], radius)
                assert copy is not None
                assert copy.value == start
                wanted = expected(nodes[start], radius)
                assert describe(copy, nodes) == wanted, (edges, start, radius)


def test_leaves_the_original_alone() -> None:
    """Changes no value and no neighbour list in the original graph."""
    nodes = graph(4, TRIANGLE_WITH_A_TAIL)
    before = [(node.value, list(node.neighbours)) for node in nodes]

    clone_graph(nodes[0], 1)

    assert [(node.value, node.neighbours) for node in nodes] == before


def test_copies_part_of_a_long_ring() -> None:
    """Copies the fifty-one nearest nodes of a ring of three hundred."""
    nodes = graph(300, [(index, (index + 1) % 300) for index in range(300)])

    copy = clone_graph(nodes[0], 25)

    assert copy is not None
    found = describe(copy, nodes)
    assert sorted(found) == [*range(26), *range(275, 300)]
    assert found == expected(nodes[0], 25)
