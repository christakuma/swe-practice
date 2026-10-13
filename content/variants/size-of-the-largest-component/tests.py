"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations

from solution import largest_component


def by_flooding(n: int, edges: list[tuple[int, int]]) -> int:
    best, seen = 0, set()
    for start in range(n):
        if start in seen:
            continue
        group, frontier = {start}, [start]
        while frontier:
            node = frontier.pop()
            for a, b in edges:
                for here, there in ((a, b), (b, a)):
                    if here == node and there not in group:
                        group.add(there)
                        frontier.append(there)
        seen |= group
        best = max(best, len(group))
    return best


def test_returns_the_size_of_the_largest() -> None:
    """Returns the node count of the biggest component."""
    assert largest_component(5, [(0, 1), (1, 2), (3, 4)]) == 3


def test_isolated_nodes_are_components_of_one() -> None:
    """Returns 1 when there are nodes and no edges."""
    assert largest_component(4, []) == 1
    assert largest_component(1, []) == 1


def test_returns_zero_for_no_nodes() -> None:
    """Returns 0 when there are no nodes."""
    assert largest_component(0, []) == 0


def test_ignores_repeated_edges_and_self_loops() -> None:
    """Does not grow a component on a repeated edge or a self-loop."""
    assert largest_component(3, [(0, 1), (1, 0), (2, 2)]) == 2
    assert largest_component(2, [(0, 1), (0, 1), (0, 1)]) == 2


def test_agrees_with_flooding_for_every_small_graph() -> None:
    """Matches a flood-fill count for every graph up to five nodes."""
    for n in range(6):
        possible = list(combinations(range(n), 2))
        for mask in range(2 ** len(possible)):
            edges = [edge for bit, edge in enumerate(possible) if mask >> bit & 1]
            assert largest_component(n, edges) == by_flooding(n, edges), (n, edges)


def test_leaves_the_edge_list_alone() -> None:
    """Does not modify the caller's list."""
    edges = [(1, 0), (2, 1)]

    largest_component(3, edges)

    assert edges == [(1, 0), (2, 1)]


def test_handles_two_hundred_thousand_nodes() -> None:
    """Handles a chain of two hundred thousand nodes within the time limit."""
    n = 200_000
    chain = [(node, node + 1) for node in range(n - 1)]

    assert largest_component(n, chain) == n
    assert largest_component(n, chain[: n // 2]) == n // 2 + 1
