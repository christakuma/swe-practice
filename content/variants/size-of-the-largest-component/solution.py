"""Reference solution. CI asserts this passes every test in `tests.py`."""


def largest_component(n: int, edges: list[tuple[int, int]]) -> int:
    """Return the size of the largest connected component.

    Union-find with a size kept at each root. Merging the smaller group into
    the larger keeps the trees shallow, and the merged size is the sum of the
    two. The `if` that skips equal roots matters twice over: it is what makes
    a repeated edge harmless, and without it a group would add its own size
    to itself.
    """
    parent = list(range(n))
    size = [1] * n

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for a, b in edges:
        first, second = find(a), find(b)
        if first == second:
            continue
        if size[first] < size[second]:
            first, second = second, first
        parent[second] = first
        size[first] += size[second]
    return max((size[find(node)] for node in range(n)), default=0)
