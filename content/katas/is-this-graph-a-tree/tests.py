"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations_with_replacement

from solution import is_tree


def reference(n: int, edges: list[tuple[int, int]]) -> bool:
    """Connected by flood fill, acyclic by the edge count -- an oracle.

    A connected graph on n nodes is acyclic exactly when it has n - 1 edges,
    so the two checks together are sufficient. It shares no bookkeeping with a
    disjoint-set solution.
    """
    if n == 0:
        return True
    adjacency: dict[int, list[int]] = {node: [] for node in range(n)}
    for a, b in edges:
        adjacency[a].append(b)
        adjacency[b].append(a)
    seen: set[int] = set()
    stack = [0]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(adjacency[node])
    return len(seen) == n and len(edges) == n - 1


def test_accepts_a_tree() -> None:
    """Reports True for a connected acyclic graph."""
    assert is_tree(5, [(0, 1), (0, 2), (0, 3), (1, 4)]) is True


def test_rejects_a_cycle() -> None:
    """Reports False when the graph contains a cycle."""
    assert is_tree(5, [(0, 1), (1, 2), (2, 3), (1, 3)]) is False


def test_rejects_a_disconnected_graph() -> None:
    """Reports False when the graph is in more than one piece.

    A forest is acyclic and is not a tree, so a solution that only looks for
    cycles accepts this.
    """
    assert is_tree(4, [(0, 1), (2, 3)]) is False


def test_rejects_isolated_nodes() -> None:
    """Reports False when a node has no edges at all."""
    assert is_tree(2, []) is False
    assert is_tree(3, [(0, 1)]) is False


def test_accepts_a_single_node() -> None:
    """Reports True for one node and no edges."""
    assert is_tree(1, []) is True


def test_accepts_no_nodes() -> None:
    """Reports True for an empty graph, vacuously.

    Without a guard, the component count is 0 rather than 1 and a
    `components == 1` test reports False.
    """
    assert is_tree(0, []) is True


def test_rejects_a_repeated_edge() -> None:
    """Treats the same edge given twice as a cycle.

    Two copies of (0, 1) are two distinct paths between the same pair, which
    is a cycle. A solution that deduplicates the edges first accepts this --
    and note the edge count is still n - 1, so a count-only check accepts it
    too.
    """
    assert is_tree(2, [(0, 1), (0, 1)]) is False
    assert is_tree(3, [(0, 1), (0, 1), (1, 2)]) is False


def test_rejects_a_self_loop() -> None:
    """Treats an edge from a node to itself as a cycle."""
    assert is_tree(1, [(0, 0)]) is False
    assert is_tree(2, [(0, 0), (0, 1)]) is False


def test_rejects_a_graph_with_the_right_edge_count_but_wrong_shape() -> None:
    """Reports False for n - 1 edges arranged as a cycle plus an island.

    Four nodes and three edges, which is exactly n - 1 -- and the graph is
    neither connected nor acyclic. The edge count alone proves nothing about
    arrangement.
    """
    assert is_tree(4, [(0, 1), (0, 1), (2, 3)]) is False
    assert is_tree(4, [(0, 1), (1, 2), (2, 0)]) is False


def test_accepts_a_long_chain() -> None:
    """Reports True for a path, which is a tree."""
    assert is_tree(5, [(0, 1), (1, 2), (2, 3), (3, 4)]) is True


def test_accepts_a_star() -> None:
    """Reports True for a star, which is also a tree."""
    assert is_tree(5, [(0, 1), (0, 2), (0, 3), (0, 4)]) is True


def test_handles_edges_given_out_of_order() -> None:
    """Accepts a tree whose edges arrive in an unhelpful order."""
    assert is_tree(5, [(3, 4), (0, 1), (2, 3), (1, 2)]) is True


def test_returns_a_bool() -> None:
    """Returns True or False rather than a truthy value."""
    assert is_tree(1, []) is True
    assert is_tree(2, []) is False


def test_agrees_with_an_oracle_on_every_small_graph() -> None:
    """Matches the oracle for every graph up to five nodes.

    Every multiset of up to five edges, self-loops and repeats included --
    around nineteen thousand graphs. Each of this kata's traps (the empty
    graph, the repeated edge, the right edge count in the wrong shape) needs a
    specific arrangement, so enumerating beats choosing.
    """
    for n in range(6):
        pairs = [(a, b) for a in range(n) for b in range(a, n)]
        for count in range(min(len(pairs), 5) + 1):
            for chosen in combinations_with_replacement(pairs, count):
                edges = list(chosen)

                assert is_tree(n, edges) is reference(n, edges), (n, edges)


def test_handles_a_large_tree() -> None:
    """Accepts a tree of two hundred thousand nodes, and rejects it plus one edge."""
    size = 200_000
    edges = [(node, node + 1) for node in range(size - 1)]

    assert is_tree(size, edges) is True
    assert is_tree(size, [*edges, (0, size - 1)]) is False
