"""Your solution goes here. The tests import `can_attend_all` from here."""


def can_attend_all(meetings: list[tuple[int, int]]) -> bool:
    """Whether one person could attend every meeting.

    A meeting is `(start, end)` and occupies `start` up to but not including
    `end`, so a meeting ending at 3 and one starting at 3 do not overlap.

    Args:
        meetings: `(start, end)` pairs with `start < end`. In any order, and
            possibly empty. Not to be modified.

    Returns:
        True if no two meetings overlap, False if any two do.
    """
    raise NotImplementedError
