"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import count_components


def recount(n: int, edges: list[tuple[int, int]]) -> int:
    """The number of components, by searching from every node."""
    neighbours: list[list[int]] = [[] for _ in range(n)]
    for first, second in edges:
        neighbours[first].append(second)
        neighbours[second].append(first)
    seen: set[int] = set()
    components = 0
    for start in range(n):
        if start in seen:
            continue
        components += 1
        stack = [start]
        seen.add(start)
        while stack:
            for neighbour in neighbours[stack.pop()]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    stack.append(neighbour)
    return components


def test_counts_down_as_components_join() -> None:
    """Lowers the count by one for each edge that joins two components."""
    assert count_components(4, [(0, 1), (2, 3), (1, 2)]) == [3, 2, 1]


def test_returns_one_entry_per_edge() -> None:
    """Returns a list exactly as long as the list of edges."""
    assert count_components(5, []) == []
    assert count_components(0, []) == []
    assert count_components(5, [(0, 4)]) == [4]


def test_a_repeated_edge_changes_nothing() -> None:
    """Repeats the previous count for an edge that was already added."""
    assert count_components(3, [(0, 1), (0, 1), (1, 0)]) == [2, 2, 2]


def test_a_self_edge_changes_nothing() -> None:
    """Keeps the count the same for an edge from a node to itself."""
    assert count_components(2, [(1, 1), (0, 0), (0, 1), (1, 1)]) == [2, 2, 1, 1]


def test_an_edge_inside_a_component_changes_nothing() -> None:
    """Keeps the count the same for an edge that closes a loop."""
    assert count_components(4, [(0, 1), (1, 2), (2, 0), (0, 3)]) == [3, 2, 2, 1]


def test_joins_groups_and_not_just_nodes() -> None:
    """Keeps a node with its group when it is joined to something else.

    0 joins 1, then 0 joins 2. If the second edge re-points node 0 instead of
    its group, node 1 is left behind and the edge between 1 and 2 looks like
    it joins two components.
    """
    assert count_components(3, [(0, 1), (0, 2), (1, 2)]) == [2, 1, 1]
    assert count_components(4, [(0, 1), (2, 3), (0, 2), (1, 3)]) == [3, 2, 1, 1]


def test_never_goes_below_one() -> None:
    """Stays at one component however many more edges arrive."""
    edges = [(0, 1), (1, 2), (0, 2), (2, 1), (0, 0), (1, 0)]

    assert count_components(3, edges) == [2, 1, 1, 1, 1, 1]


def test_agrees_with_recounting_after_every_edge() -> None:
    """Matches a full recount after each edge, for every short sequence.

    Every sequence of up to three edges on four nodes, self-edges and repeats
    included.
    """
    pairs = list(product(range(4), repeat=2))
    for length in range(1, 4):
        for chosen in product(pairs, repeat=length):
            edges = list(chosen)
            expected = [recount(4, edges[: index + 1]) for index in range(length)]
            assert count_components(4, edges) == expected, edges


def test_leaves_the_edges_alone() -> None:
    """Does not modify the list of edges."""
    edges = [(2, 0), (1, 2)]

    count_components(3, edges)

    assert edges == [(2, 0), (1, 2)]


def test_handles_two_hundred_thousand_edges() -> None:
    """Answers after each of 200,000 edges within the time limit.

    A chain built one link at a time, so the count falls by one per edge all
    the way from 199,999 to 1, followed by a repeat of the last link. A fresh
    search after every edge is twenty thousand million steps.
    """
    n = 200_000
    edges = [(node, node + 1) for node in range(n - 1)] + [(n - 2, n - 1)]

    counts = count_components(n, edges)

    assert counts[: n - 1] == list(range(n - 1, 0, -1))
    assert counts[-1] == 1


def test_handles_edges_that_arrive_in_a_bad_order() -> None:
    """Stays fast when every edge hangs one more node off a long chain's far end."""
    n = 100_000
    edges = [(node + 1, node) for node in reversed(range(n - 1))]

    counts = count_components(n, edges)

    assert counts == list(range(n - 1, 0, -1))
