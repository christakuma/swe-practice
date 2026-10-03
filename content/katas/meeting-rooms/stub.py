"""Your solution goes here. The tests import `rooms_needed` from here."""


def rooms_needed(meetings: list[tuple[int, int]]) -> int:
    """Return the fewest rooms that can hold every meeting.

    A meeting is `(start, end)` and occupies the room for `start` up to but not
    including `end`, so a meeting ending at 3 and one starting at 3 can share.

    Args:
        meetings: `(start, end)` pairs with `start < end`. In any order.

    Returns:
        The largest number of meetings that overlap at any one moment.
    """
    raise NotImplementedError
