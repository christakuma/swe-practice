"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, combinations_with_replacement

from solution import count_components


def reference(n: int, edges: list[tuple[int, int]]) -> int:
    """Count components by flood-filling an adjacency map -- an oracle.

    It shares nothing with a disjoint-set solution: no parents, no ranks, no
    amortisation.
    """
    adjacency: dict[int, set[int]] = {node: set() for node in range(n)}
    for a, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)
    seen: set[int] = set()
    count = 0
    for start in range(n):
        if start in seen:
            continue
        count += 1
        stack = [start]
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            stack.extend(adjacency[node])
    return count


def test_counts_two_components() -> None:
    """Counts a three-node chain and a two-node edge as two components."""
    assert count_components(5, [(0, 1), (1, 2), (3, 4)]) == 2


def test_counts_isolated_nodes() -> None:
    """Counts every node separately when there are no edges."""
    assert count_components(5, []) == 5
    assert count_components(1, []) == 1


def test_handles_no_nodes() -> None:
    """Returns zero when there are no nodes."""
    assert count_components(0, []) == 0


def test_counts_a_fully_connected_graph() -> None:
    """Counts one component when everything is joined."""
    assert count_components(4, [(0, 1), (1, 2), (2, 3)]) == 1
    assert count_components(4, [(0, 1), (0, 2), (0, 3)]) == 1


def test_ignores_a_redundant_edge() -> None:
    """Does not decrement for an edge joining nodes already together.

    The triangle has three edges and one component. A solution that subtracts
    one per edge regardless reports -1 or 0.
    """
    assert count_components(3, [(0, 1), (1, 2), (0, 2)]) == 1


def test_ignores_duplicate_edges() -> None:
    """Handles the same edge given more than once."""
    assert count_components(3, [(0, 1), (0, 1), (0, 1)]) == 2
    assert count_components(2, [(0, 1), (1, 0)]) == 1


def test_ignores_a_self_loop() -> None:
    """Handles an edge from a node to itself."""
    assert count_components(3, [(0, 0)]) == 3
    assert count_components(3, [(0, 0), (1, 2)]) == 2


def test_handles_edges_given_out_of_order() -> None:
    """Merges components regardless of the order edges arrive in.

    The first two edges create two separate pairs and the third joins them, so
    a solution that only ever attaches a node to an existing component -- never
    merging two -- reports 2.
    """
    assert count_components(4, [(0, 1), (2, 3), (1, 2)]) == 1
    assert count_components(6, [(4, 5), (0, 1), (2, 3), (1, 3), (3, 5)]) == 1


def test_handles_a_chain_built_backwards() -> None:
    """Merges a chain whose edges arrive from the far end."""
    edges = [(3, 4), (2, 3), (1, 2), (0, 1)]

    assert count_components(5, edges) == 1


def test_returns_a_plain_integer() -> None:
    """Returns an int rather than a bool."""
    assert type(count_components(2, [(0, 1)])) is int


def test_does_not_mutate_the_edge_list() -> None:
    """Leaves the caller's edge list alone."""
    edges = [(0, 1), (2, 3)]
    before = list(edges)

    count_components(4, edges)

    assert edges == before


def test_agrees_with_a_flood_fill_on_every_small_graph() -> None:
    """Matches a flood-fill count for every graph up to five nodes.

    Every selection of up to four distinct edges, including self-loops --
    around three thousand graphs. The redundant-edge bug and the
    merge-two-components bug each need a particular edge ordering, so
    enumerating beats choosing.
    """
    for n in range(6):
        pairs = [(a, b) for a in range(n) for b in range(a, n)]
        for count in range(min(len(pairs), 4) + 1):
            for chosen in combinations(pairs, count):
                edges = list(chosen)

                assert count_components(n, edges) == reference(n, edges), (n, edges)


def test_agrees_with_a_flood_fill_when_edges_repeat() -> None:
    """Matches the oracle for multisets of edges, duplicates included."""
    for n in range(1, 5):
        pairs = [(a, b) for a in range(n) for b in range(n)]
        for count in range(4):
            for chosen in combinations_with_replacement(pairs, count):
                edges = list(chosen)

                assert count_components(n, edges) == reference(n, edges), (n, edges)


def test_handles_a_large_graph() -> None:
    """Counts components among two hundred thousand nodes.

    Built as a thousand separate chains, and the edges are shuffled
    deterministically so a component is assembled from unions arriving out of
    order -- which is where a structure without union-by-size builds tall
    trees and finding degrades to linear.
    """
    chains = 1_000
    per_chain = 200
    size = chains * per_chain
    edges = [
        (chain * per_chain + step, chain * per_chain + step + 1)
        for step in range(per_chain - 1)
        for chain in range(chains)
    ]

    assert count_components(size, edges) == chains
