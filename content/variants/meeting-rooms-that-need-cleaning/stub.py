"""Your solution goes here. The tests import from this module."""


def rooms_needed(meetings: list[tuple[int, int]], gap: int) -> int:
    """Return the fewest rooms that can hold all the meetings, with cleaning.

    Args:
        meetings: `(start, end)` pairs with `start < end`, in any order.
        gap: how long a room must stand empty after a meeting. Zero or more.

    Returns:
        The smallest number of rooms such that no room hosts two meetings
        less than `gap` apart.
    """
    raise NotImplementedError
