"""Your solution goes here. The tests import `topological_order` from here."""


def topological_order(dependencies: dict[str, list[str]]) -> list[str] | None:
    """Order the names so that every name comes after everything it depends on.

    Args:
        dependencies: name to the names it depends on. A name may appear only
            as a dependency and never as a key.

    Returns:
        A valid order, or None if no order exists because of a cycle. Where
        several orders are valid, the alphabetically smallest available name is
        chosen at each step, so the result is deterministic.
    """
    raise NotImplementedError
