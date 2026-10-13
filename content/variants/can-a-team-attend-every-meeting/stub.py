"""Your solution goes here. The tests import from this module."""


def can_attend_all(meetings: list[tuple[int, int]], people: int) -> bool:
    """Whether `people` people can cover every meeting between them.

    Args:
        meetings: `(start, end)` pairs with `start < end`, half-open, in any
            order. Not to be modified.
        people: how many people there are. Zero or more.

    Returns:
        True if at no moment are more meetings in progress than there are
        people.
    """
    raise NotImplementedError
