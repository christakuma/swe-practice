"""Reference solution. CI asserts this passes every test in `tests.py`."""


def redundant_edge(n: int, edges: list[tuple[int, int]]) -> tuple[int, int]:
    """Return the last edge whose removal leaves a tree.

    Adding the edges in order, each one joins two components until the one
    that finds its ends already joined: that edge closes the only cycle.
    Every other edge on the cycle was added before it, so it is also the
    last removable edge in the input, which is what was asked for.
    """
    parent = list(range(n))

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for a, b in edges:
        first, second = find(a), find(b)
        if first == second:
            return (a, b)
        parent[first] = second
    raise ValueError("the edges contain no cycle")
