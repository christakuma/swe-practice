"""Reference solution. CI asserts this passes every test in `tests.py`."""


def can_attend_all(meetings: list[tuple[int, int]], people: int) -> bool:
    """Whether `people` people can cover every meeting between them.

    The team suffices exactly when the peak number of simultaneous meetings
    is at most `people`. Starts and ends are sorted separately: which end
    belongs to which start does not matter for a count. `<=` when releasing,
    because a meeting that ends as another starts has already freed its
    person.
    """
    starts = sorted(start for start, _ in meetings)
    ends = sorted(end for _, end in meetings)
    released = 0
    for begun, start in enumerate(starts, start=1):
        while ends[released] <= start:
            released += 1
        if begun - released > people:
            return False
    return True
