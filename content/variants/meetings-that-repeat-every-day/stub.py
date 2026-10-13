"""Your solution goes here. The tests import from this module."""


def can_attend_all(meetings: list[tuple[int, int]]) -> bool:
    """Whether one person could attend every meeting, every day.

    Args:
        meetings: `(start, end)` pairs in minutes after midnight, each from 0
            to 1439 and never equal. Half-open. An `end` smaller than its
            `start` means the meeting runs through midnight. In any order,
            possibly repeated. Not to be modified.

    Returns:
        True if no two meetings are ever in progress at the same minute.
    """
    raise NotImplementedError
