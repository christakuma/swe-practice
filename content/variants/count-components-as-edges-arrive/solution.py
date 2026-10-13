"""Reference solution. CI asserts this passes every test in `tests.py`."""


def count_components(n: int, edges: list[tuple[int, int]]) -> list[int]:
    """Return the number of components after each edge is added.

    The count starts at `n` and an edge can only do one thing to it: lower it
    by one, when its ends were in different components. So the whole problem
    is asking "are these two already connected?" two hundred thousand times,
    against a graph that keeps growing -- which is union-find's one job.

    `find` walks to a root and halves the path as it goes; the smaller tree is
    hung under the larger. Together those keep every walk a few steps long
    whatever order the edges arrive in.
    """
    parent = list(range(n))
    size = [1] * n

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    components = n
    counts: list[int] = []
    for first, second in edges:
        first_root, second_root = find(first), find(second)
        if first_root != second_root:
            if size[first_root] < size[second_root]:
                first_root, second_root = second_root, first_root
            parent[second_root] = first_root
            size[first_root] += size[second_root]
            components -= 1
        counts.append(components)
    return counts
