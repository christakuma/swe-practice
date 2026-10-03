"""Reference solution. CI asserts this passes every test in `tests.py`."""

import heapq


def rooms_needed(meetings: list[tuple[int, int]]) -> int:
    """Return the fewest rooms that can hold every meeting.

    Sort by start, and keep a heap of the end times of the meetings currently in
    progress. For each new meeting, if the earliest-ending room has freed up by
    then, reuse it; otherwise open another. The heap's size at the end is the
    answer -- it never shrinks, because it is a high-water mark.

    The heap is there to answer one question: *which room frees up first*. That
    is the only room worth checking, because if the earliest-ending meeting has
    not finished, none of the others have either. A list scanned for the minimum
    is the same algorithm at O(n^2); the heap makes it O(n log n), the same cost
    as the sort it already pays.

    `ends[0] <= start` rather than `<`, because the intervals are half-open: a
    meeting ending at 3 and one starting at 3 do not overlap. That is the
    opposite convention to `merge-intervals`, where the intervals are closed and
    touching counts as overlapping -- and the difference is one character in each
    case, which is why both exercises state it in the prompt.

    The other standard solution is a sweep: sort all the starts and all the ends
    separately, then walk the merged timeline adding one at a start and
    subtracting at an end, tracking the maximum. Same complexity, no heap, and it
    loses the ability to say *which* room each meeting is in.
    """
    ends: list[int] = []
    for start, end in sorted(meetings):
        if ends and ends[0] <= start:
            heapq.heapreplace(ends, end)
        else:
            heapq.heappush(ends, end)
    return len(ends)
