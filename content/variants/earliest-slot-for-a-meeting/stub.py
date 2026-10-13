"""Your solution goes here."""


def earliest_slot(
    meetings: list[tuple[int, int]], duration: int, opens: int, closes: int
) -> int | None:
    """Return the earliest start for a new meeting, or None if none fits.

    A meeting is `(start, end)` and occupies `start` up to but not including
    `end`.

    Args:
        meetings: `(start, end)` pairs with `start < end`. In any order,
            possibly empty, possibly overlapping one another. Not to be
            modified.
        duration: the length of the meeting to place. At least 1.
        opens: the earliest the new meeting may start.
        closes: the latest the new meeting may end. Later than `opens`.

    Returns:
        The smallest start time at which a meeting of `duration` lies within
        `opens..closes` and overlaps no existing meeting. None if there is
        none.
    """
    raise NotImplementedError
