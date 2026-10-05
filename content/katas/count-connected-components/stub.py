"""Your solution goes here.

The tests import `count_components` from this module.
"""


def count_components(n: int, edges: list[tuple[int, int]]) -> int:
    """Count the connected components among `n` labelled nodes.

    Args:
        n: how many nodes there are, labelled 0 to n - 1. May be 0.
        edges: undirected edges as (a, b) pairs. May repeat, and may join
            nodes that are already connected.

    Returns:
        The number of connected components. An isolated node counts as one.
    """
    raise NotImplementedError
