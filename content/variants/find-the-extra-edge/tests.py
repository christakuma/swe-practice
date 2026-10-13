"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations

from solution import redundant_edge


def is_tree(n: int, edges: list[tuple[int, int]]) -> bool:
    if len(edges) != n - 1:
        return False
    reached, frontier = {0}, [0]
    while frontier:
        node = frontier.pop()
        for a, b in edges:
            for here, there in ((a, b), (b, a)):
                if here == node and there not in reached:
                    reached.add(there)
                    frontier.append(there)
    return len(reached) == n


def by_removing(n: int, edges: list[tuple[int, int]]) -> tuple[int, int]:
    """Try removing each edge, last first, until what is left is a tree."""
    for at in range(len(edges) - 1, -1, -1):
        if is_tree(n, edges[:at] + edges[at + 1 :]):
            return edges[at]
    raise AssertionError


def test_returns_the_last_edge_of_a_triangle() -> None:
    """Returns the last edge when every edge is on the cycle."""
    assert redundant_edge(3, [(0, 1), (0, 2), (1, 2)]) == (1, 2)


def test_ignores_a_later_edge_that_is_not_on_the_cycle() -> None:
    """Does not return an edge whose removal would disconnect the graph."""
    edges = [(0, 1), (1, 2), (2, 3), (0, 3), (0, 4)]

    assert redundant_edge(5, edges) == (0, 3)


def test_is_not_fooled_by_ends_it_has_merely_seen() -> None:
    """Asks whether the ends are connected, not whether they have appeared.

    When (1, 2) arrives, both of its ends have been seen in earlier edges --
    and they are in different pieces, so it closes nothing.
    """
    assert redundant_edge(4, [(0, 1), (2, 3), (1, 2), (0, 3)]) == (0, 3)


def test_returns_the_edge_as_it_was_given() -> None:
    """Returns the edge in the orientation it had in the input."""
    assert redundant_edge(3, [(1, 0), (2, 1), (2, 0)]) == (2, 0)
    assert redundant_edge(3, [(1, 0), (2, 1), (0, 2)]) == (0, 2)


def test_agrees_with_removing_each_edge_in_turn() -> None:
    """Matches a remove-and-check search for every small graph, both ways round."""
    for n in range(3, 6):
        for chosen in combinations(list(combinations(range(n), 2)), n):
            edges = list(chosen)
            reached = {0}
            for _ in range(n):
                reached |= {b for a, b in edges if a in reached} | {
                    a for a, b in edges if b in reached
                }
            if len(reached) != n:
                continue
            for ordering in (edges, edges[::-1]):
                assert redundant_edge(n, list(ordering)) == by_removing(n, ordering)


def test_handles_a_large_cycle() -> None:
    """Finds the closing edge of a cycle of two hundred thousand nodes."""
    n = 200_000
    ring = [(node, node + 1) for node in range(n - 1)]

    assert redundant_edge(n, [*ring, (n - 1, 0)]) == (n - 1, 0)
    assert redundant_edge(n, [(0, n - 1), *ring]) == (n - 2, n - 1)
