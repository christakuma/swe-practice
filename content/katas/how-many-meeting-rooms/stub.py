"""Your solution goes here.

The tests import `rooms_needed` from this module.
"""


def rooms_needed(meetings: list[tuple[int, int]]) -> int:
    """Return the fewest rooms that can hold all the meetings.

    Args:
        meetings: `(start, end)` pairs with `start < end`, in any order. May
            be empty and may repeat. A meeting ending when another starts
            shares its room.

    Returns:
        The maximum number of meetings running simultaneously.
    """
    raise NotImplementedError
