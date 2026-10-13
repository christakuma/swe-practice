"""Reference solution. CI asserts this passes every test in `tests.py`."""


def find_root(n: int, edges: list[tuple[int, int]]) -> int | None:
    """Return the root if the directed edges form a rooted tree, else None.

    Two checks, and the second exists because of what the first cannot see.

    **Parent counts.** One node with none, the rest with exactly one. This
    catches two roots, a node with two parents, repeated edges and
    self-loops, and it fixes the number of edges at `n - 1`.

    **Reachability.** A cycle that does not include the root gives each of
    its nodes one parent, so the counts look perfect. But nothing on such a
    cycle can be reached from the root -- reaching it would need a second
    parent. So walk down from the root and count: a tree reaches all `n`.

    The walk needs no visited set. With every node having at most one parent,
    no node can be arrived at twice.
    """
    parents = [0] * n
    children: list[list[int]] = [[] for _ in range(n)]
    for parent, child in edges:
        parents[child] += 1
        children[parent].append(child)

    roots = [node for node in range(n) if parents[node] == 0]
    if len(roots) != 1 or any(count > 1 for count in parents):
        return None

    reached = 0
    pending = roots[:]
    while pending:
        node = pending.pop()
        reached += 1
        pending.extend(children[node])
    return roots[0] if reached == n else None
