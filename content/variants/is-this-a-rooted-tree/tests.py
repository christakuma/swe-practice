"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import find_root

type Edges = list[tuple[int, int]]


def by_trying_every_root(n: int, edges: Edges) -> int | None:
    """A rooted tree has n - 1 edges and a node from which every node is reachable."""
    if len(edges) != n - 1:
        return None
    for root in range(n):
        reached = {root}
        grew = True
        while grew:
            grew = False
            for parent, child in edges:
                if parent in reached and child not in reached:
                    reached.add(child)
                    grew = True
        if len(reached) == n:
            return root
    return None


def test_finds_the_root_of_a_tree() -> None:
    """Returns the one node with no parent when the edges form a tree."""
    assert find_root(4, [(2, 0), (2, 3), (3, 1)]) == 2
    assert find_root(3, [(0, 1), (0, 2)]) == 0


def test_the_root_need_not_be_node_zero_or_come_first() -> None:
    """Finds a root with any label, wherever its edges are in the list."""
    assert find_root(4, [(0, 1), (3, 0), (3, 2)]) == 3
    assert find_root(2, [(1, 0)]) == 1


def test_a_single_node_is_a_tree() -> None:
    """Returns 0 for one node and no edges."""
    assert find_root(1, []) == 0


def test_a_node_with_two_parents_is_not_a_tree() -> None:
    """Rejects edges that would be a tree if their directions were ignored."""
    assert find_root(3, [(0, 1), (2, 1)]) is None
    assert find_root(4, [(0, 1), (0, 2), (1, 3), (2, 3)]) is None


def test_two_separate_trees_are_not_a_tree() -> None:
    """Rejects a forest, which has more than one node without a parent."""
    assert find_root(4, [(0, 1), (2, 3)]) is None
    assert find_root(2, []) is None


def test_a_loop_the_root_cannot_reach_is_not_a_tree() -> None:
    """Rejects a cycle beside the root, where every parent count looks right.

    Node 0 has no parent and every other node has exactly one, in both
    graphs. The nodes on the loop are each other's parents.
    """
    assert find_root(3, [(1, 2), (2, 1)]) is None
    assert find_root(5, [(0, 1), (2, 3), (3, 4), (4, 2)]) is None


def test_a_cycle_through_every_node_has_no_root() -> None:
    """Rejects a ring, in which every node has a parent."""
    assert find_root(3, [(0, 1), (1, 2), (2, 0)]) is None


def test_an_edge_back_to_the_root_is_not_a_tree() -> None:
    """Rejects a tree with one extra edge pointing back up at its root."""
    assert find_root(3, [(0, 1), (1, 2), (2, 0), (0, 2)]) is None
    assert find_root(2, [(0, 1), (1, 0)]) is None


def test_a_repeated_edge_is_two_parents() -> None:
    """Rejects the same edge given twice."""
    assert find_root(2, [(0, 1), (0, 1)]) is None
    assert find_root(3, [(0, 1), (0, 1), (0, 2)]) is None


def test_a_self_edge_is_not_a_tree() -> None:
    """Rejects a node that is its own parent."""
    assert find_root(1, [(0, 0)]) is None
    assert find_root(2, [(0, 1), (1, 1)]) is None
    assert find_root(2, [(0, 0), (0, 1)]) is None


def test_agrees_with_trying_every_root() -> None:
    """Matches a reachability search from every node, for every small graph.

    Every list of up to three edges on three nodes and on four nodes,
    self-edges and repeats included.
    """
    for n in (1, 2, 3, 4):
        pairs = list(product(range(n), repeat=2))
        for length in range(4):
            for chosen in product(pairs, repeat=length):
                edges = list(chosen)
                assert find_root(n, edges) == by_trying_every_root(n, edges), (n, edges)


def test_leaves_the_edges_alone() -> None:
    """Does not modify the list of edges."""
    edges = [(1, 0), (1, 2)]

    find_root(3, edges)

    assert edges == [(1, 0), (1, 2)]


def test_handles_a_very_deep_tree() -> None:
    """Handles a chain of 100,000 nodes without recursing.

    Reversing the chain's top link moves the root down by one. Adding an edge
    from the bottom back to the top leaves no root at all.
    """
    n = 100_000
    chain = [(node + 1, node) for node in range(n - 1)]

    assert find_root(n, chain) == n - 1
    assert find_root(n, [*chain[:-1], (n - 2, n - 1)]) == n - 2
    assert find_root(n, [*chain, (0, n - 1)]) is None


def test_handles_a_large_tree_and_a_large_near_miss() -> None:
    """Handles 200,000 nodes, as a tree and with one node re-parented into a loop.

    In the second graph the last three nodes point at one another in a ring.
    Every node except the root still has exactly one parent.
    """
    n = 200_000
    tree = [((child - 1) // 2, child) for child in range(1, n)]
    looped = [*tree[:-3], (n - 1, n - 3), (n - 3, n - 2), (n - 2, n - 1)]

    assert find_root(n, tree) == 0
    assert find_root(n, looped) is None
