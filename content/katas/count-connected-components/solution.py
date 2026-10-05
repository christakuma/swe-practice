"""Reference solution. CI asserts this passes every test in `tests.py`."""


def count_components(n: int, edges: list[tuple[int, int]]) -> int:
    """Count the connected components among `n` labelled nodes.

    Start from the answer with no edges: `n` components, one per node. Then
    **every edge that joins two different components reduces the count by
    one**, and every edge joining nodes already together changes nothing. So
    the whole problem is answering "are these two together?" and "put them
    together" repeatedly -- which is a disjoint-set (union-find) structure.

    `parent` holds each node's representative. Two nodes are in the same
    component exactly when their representatives match, so `find` walks up the
    parent chain to the root.

    Two refinements turn that from quadratic into effectively linear, and both
    are one line:

    **Path compression** -- `parent[node] = parent[parent[node]]` -- points
    every node passed on the way up at its grandparent, halving the chain each
    traversal. Repeated finds flatten the structure as a side effect of using
    it, which is unusual and the reason this works so well: the data structure
    gets cheaper the more it is queried.

    **Union by size** -- attach the smaller tree under the larger -- stops a
    chain of unions building a tall tree in the first place. Without it,
    unioning 0-1, then 1-2, then 2-3 can produce a linear chain and `find`
    degrades to O(V).

    Together these give O(almost constant) amortised per operation (inverse
    Ackermann, which is below 5 for any input that fits in memory).

    A breadth- or depth-first search over an adjacency list is the other good
    answer and is O(V + E) outright, with no amortised hand-waving. Union-find
    wins when the edges *arrive over time* -- it answers connectivity after
    each one without rebuilding anything, which a traversal cannot.
    """
    parent = list(range(n))
    size = [1] * n
    components = n

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]  # path compression
            node = parent[node]
        return node

    for a, b in edges:
        root_a, root_b = find(a), find(b)
        if root_a == root_b:
            continue  # already together; this edge is redundant
        if size[root_a] < size[root_b]:
            root_a, root_b = root_b, root_a
        parent[root_b] = root_a
        size[root_a] += size[root_b]
        components -= 1

    return components
