"""Reference solution. CI asserts this passes every test in `tests.py`."""

import heapq


def rooms_needed(meetings: list[tuple[int, int]], gap: int) -> int:
    """Return the fewest rooms that can hold all the meetings, with cleaning.

    The heap holds the end time of the meeting in each room. Taking the
    meetings in order of start, only the room that finished earliest is worth
    checking, and it can be reused when it has been empty for `gap`. The
    heap's final size is the answer: it only ever grows.
    """
    ends: list[int] = []
    for start, end in sorted(meetings):
        if ends and ends[0] + gap <= start:
            heapq.heapreplace(ends, end)
        else:
            heapq.heappush(ends, end)
    return len(ends)
