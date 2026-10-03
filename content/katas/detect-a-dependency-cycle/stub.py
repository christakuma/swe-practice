"""Your solution goes here. The tests import `has_cycle` from here."""


def has_cycle(dependencies: dict[str, list[str]]) -> bool:
    """Whether the dependency graph contains a cycle.

    `dependencies[a]` lists the things `a` depends on, so an edge runs from `a`
    to each of them. A name may appear only as a dependency and never as a key.

    Args:
        dependencies: name to the names it depends on. May be empty.

    Returns:
        True if any chain of dependencies leads back to where it started.
    """
    raise NotImplementedError
