"""Reference solution. CI asserts this passes every test in `tests.py`."""

from itertools import pairwise


def can_attend_all(meetings: list[tuple[int, int]]) -> bool:
    """Whether one person could attend every meeting.

    Sort by start and compare neighbours. That is enough because of what the
    sort guarantees: if a meeting overlapped one further along than its
    neighbour, the neighbour -- which starts no later than that one -- would
    start before this meeting ends too. So the first clash, if there is one, is
    always between two meetings that are adjacent in start order.

    `sorted` rather than `list.sort`: the caller's list is not this function's
    to reorder, and a predicate that rearranges its argument is a surprise.

    Strictly `<`. Half-open intervals mean a meeting that starts exactly when
    the previous one ends is fine, and `<=` would call that a clash.
    """
    ordered = sorted(meetings)
    return all(following[0] >= previous[1] for previous, following in pairwise(ordered))
