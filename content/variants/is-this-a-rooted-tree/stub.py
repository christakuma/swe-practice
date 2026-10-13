"""Your solution goes here. The tests import `find_root` from this module."""


def find_root(n: int, edges: list[tuple[int, int]]) -> int | None:
    """Return the root if the directed edges form a rooted tree, else None.

    Args:
        n: the number of nodes, labelled 0 to n - 1. At least 1.
        edges: `(parent, child)` pairs. May repeat, and may join a node to
            itself.

    Returns:
        The label of the one node with no parent, provided every other node
        has exactly one parent and all of them can be reached from it.
        None otherwise.
    """
    raise NotImplementedError
