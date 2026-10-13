"""Your solution goes here. The tests import from this module."""


def redundant_edge(n: int, edges: list[tuple[int, int]]) -> tuple[int, int]:
    """Return the last edge whose removal leaves a tree.

    Args:
        n: how many nodes there are, labelled 0 to n - 1.
        edges: exactly n undirected edges forming a tree plus one extra.

    Returns:
        The edge, as given, that appears last in `edges` among those that
        could be removed to leave a tree.
    """
    raise NotImplementedError
