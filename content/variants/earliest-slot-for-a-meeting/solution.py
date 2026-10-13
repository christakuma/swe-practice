"""Reference solution. CI asserts this passes every test in `tests.py`."""


def earliest_slot(
    meetings: list[tuple[int, int]], duration: int, opens: int, closes: int
) -> int | None:
    """Return the earliest start for a new meeting, or None if none fits.

    `free_from` is the earliest moment at which every meeting examined so far
    has finished. Walking the meetings in order of start, the stretch from
    `free_from` to the next meeting's start is free -- nothing examined
    reaches into it, and nothing still to come starts before it ends. If
    that stretch is long enough, `free_from` is the answer, and it is the
    earliest because every earlier moment was inside a meeting or a gap
    already found too short.

    `max` is what makes it right for a diary that overlaps itself. A meeting
    nested inside a longer one ends first, and taking its end as the new
    `free_from` would move the moment *backwards* into the longer meeting.

    The day's bounds need almost nothing. Starting `free_from` at `opens`
    handles meetings that begin before the day does, by the same `max`. The
    single test against `closes` at the end handles both ways out of the
    loop: a gap found between meetings must still finish inside the day, and
    running out of meetings leaves the gap after the last one to be judged.
    """
    free_from = opens
    for start, end in sorted(meetings):
        if start - free_from >= duration:
            break
        free_from = max(free_from, end)
    return free_from if closes - free_from >= duration else None
