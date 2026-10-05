"""Reference solution. CI asserts this passes every test in `tests.py`."""


def is_tree(n: int, edges: list[tuple[int, int]]) -> bool:
    """Return whether the graph is a tree: connected and acyclic.

    Two independent properties, and a single pass over the edges establishes
    both -- which is the pleasing part of using union-find here rather than a
    traversal.

    **Acyclic** falls straight out of the structure: a cycle is exactly an edge
    whose two endpoints are *already* in the same component. Nothing else needs
    checking, and there is no separate cycle search. Note what this buys for
    free -- a repeated edge is correctly rejected, because the second copy finds
    the endpoints already joined. A repeated undirected edge genuinely is a
    cycle (two distinct paths between the same pair), and a solution that
    deduplicates edges first silently accepts it.

    **Connected** is then a count: after all the edges, exactly one component
    must remain.

    `n == 0` returns True before anything else. An empty graph is vacuously a
    tree, and without the guard the component count is 0 rather than 1 and the
    answer comes out False.

    There is a well-known shortcut: a graph with `n` nodes and exactly `n - 1`
    edges is a tree **if and only if it is connected**. The forward direction
    is the useful one -- any acyclic connected graph has exactly n - 1 edges --
    and it lets you replace the cycle check with `len(edges) == n - 1`.

    It is only safe *alongside* a connectivity check, and the trap is using the
    edge count alone: `(0,1), (0,1), (2,3)` on four nodes has three edges,
    which is n - 1, and is neither connected nor acyclic. The count rules out
    "too few" and "too many" edges; it says nothing about how they are
    arranged. The version below checks both properties directly because that is
    what the problem asks, and the shortcut is a consequence rather than a
    definition.
    """
    if n == 0:
        return True

    parent = list(range(n))
    size = [1] * n
    components = n

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for a, b in edges:
        root_a, root_b = find(a), find(b)
        if root_a == root_b:
            return False  # both ends already joined: this edge closes a cycle
        if size[root_a] < size[root_b]:
            root_a, root_b = root_b, root_a
        parent[root_b] = root_a
        size[root_a] += size[root_b]
        components -= 1

    return components == 1
