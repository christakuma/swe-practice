"""Reference solution. CI asserts this passes every test in `tests.py`."""


def rooms_needed(meetings: list[tuple[int, int]]) -> int:
    """Return the fewest rooms that can hold all the meetings.

    **Stop thinking about rooms.** The answer is the largest number of meetings
    running at the same moment -- a property of the timeline, not an assignment
    problem. Once that is the question, no meeting is ever placed anywhere and
    there is nothing to pack.

    The count only changes when something starts or ends, so only those moments
    matter. Sweep the starts and the ends in time order, +1 at a start, -1 at
    an end, and record the peak. The two sorted lists are deliberately
    **decoupled** -- a start and the end it belongs to are never looked at
    together, because the identity of the meeting is irrelevant to how many are
    running.

    That decoupling is what makes it O(n log n) with two pointers and no heap,
    and it is the part worth noticing: the obvious model (keep a heap of end
    times, pop the ones that have finished) also works and is the version most
    people write. Both are O(n log n). The sweep is simpler because it never
    needs to know *which* meeting ended.

    **Ends before starts on a tie.** A meeting ending exactly when another
    begins shares a room, so at an equal timestamp the -1 must be applied
    first. `ends[finished] <= starts[index]` is where that lives, and using `<`
    counts touching meetings as overlapping -- the same endpoint convention as
    the neighbouring interval katas, where it decides whether intervals merge
    or coexist.

    `peak` never decreases and both pointers only move forward, so the sweep is
    one pass after the sorts.

    The `finished < len(ends)` bound is not reachable for in-contract input --
    a meeting has positive duration, so some meeting is always still running
    when the next one starts. It is there because a zero-width meeting, which
    the prompt excludes, would otherwise walk the pointer off the end and
    raise. A guard that costs one comparison and turns a crash into a
    defensible answer is worth keeping even when the contract forbids the
    input.
    """
    if not meetings:
        return 0

    starts = sorted(start for start, _ in meetings)
    ends = sorted(end for _, end in meetings)

    running = peak = 0
    finished = 0
    for start in starts:
        while finished < len(ends) and ends[finished] <= start:
            running -= 1
            finished += 1
        running += 1
        peak = max(peak, running)
    return peak
