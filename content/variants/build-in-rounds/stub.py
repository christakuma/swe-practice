"""Your solution goes here. The tests import from this module."""


def build_rounds(dependencies: dict[str, list[str]]) -> list[list[str]] | None:
    """Group the names into rounds that depend only on earlier rounds.

    Args:
        dependencies: name to the names it depends on. A name may appear only
            as a dependency and never as a key.

    Returns:
        The rounds in order, each sorted ascending, with every name in the
        earliest round it can be in. None if there is a cycle.
    """
    raise NotImplementedError
