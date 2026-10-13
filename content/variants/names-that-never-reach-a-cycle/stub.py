"""Your solution goes here. The tests import from this module."""


def safe_names(dependencies: dict[str, list[str]]) -> list[str]:
    """Return the names from which no chain of dependencies reaches a cycle.

    Args:
        dependencies: name to the names it depends on. May be empty. A name
            may appear only as a dependency and never as a key.

    Returns:
        The safe names, sorted ascending.
    """
    raise NotImplementedError
