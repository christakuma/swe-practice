"""Your solution goes here. The tests import `count_components` from this module."""


def count_components(n: int, edges: list[tuple[int, int]]) -> list[int]:
    """Return the number of components after each edge is added.

    Args:
        n: the number of nodes, labelled 0 to n - 1.
        edges: undirected edges, added in this order. May repeat, and may
            join a node to itself.

    Returns:
        A list as long as `edges`. Entry i is the number of connected
        components once edges 0 to i are all in place.
    """
    raise NotImplementedError
