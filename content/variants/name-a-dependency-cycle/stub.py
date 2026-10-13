"""Your solution goes here. The tests import `find_cycle` from this module."""


def find_cycle(dependencies: dict[str, list[str]]) -> list[str] | None:
    """Return the names of one dependency cycle, in order.

    Args:
        dependencies: each name mapped to the names it depends on. A name may
            appear only as a dependency, with no entry of its own.

    Returns:
        A list of distinct names in which each depends on the next and the
        last depends on the first, or None if the graph has no cycle.
    """
    raise NotImplementedError
