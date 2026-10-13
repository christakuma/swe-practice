"""Your solution goes here. The tests import `assign_rooms` from this module."""


def assign_rooms(meetings: list[tuple[int, int]]) -> list[int]:
    """Return the room each meeting is given.

    Meetings are booked in order of start time, ties broken by position in
    the input, and each takes the lowest-numbered room that is free.

    Args:
        meetings: `(start, end)` pairs with `start < end`, in any order. May
            be empty and may repeat. A meeting ending when another starts
            frees its room in time.

    Returns:
        A list as long as `meetings`. Entry i is the room number, counting
        from 0, of the meeting at position i of the input.
    """
    raise NotImplementedError
