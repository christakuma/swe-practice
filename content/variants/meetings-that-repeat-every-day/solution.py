"""Reference solution. CI asserts this passes every test in `tests.py`."""

DAY = 24 * 60


def can_attend_all(meetings: list[tuple[int, int]]) -> bool:
    """Whether one person could attend every meeting, every day.

    Each meeting is rewritten as a start and a **length**, `(end - start) %
    DAY`, which is the same sum whichever side of midnight it finishes on --
    so an `end` smaller than its `start` stops being a special case before
    anything is compared.

    Then the standard version's argument holds on the circle: sorted by
    start, a meeting that reaches past the next start is in progress when the
    next one begins, and if none does, each sits wholly between its own start
    and the next. What the circle adds is one more pair. The last meeting in
    start order is followed by the first, tomorrow, and that start is written
    here as the first start plus a day, so the same comparison covers it.

    A single meeting is followed by itself a whole day later, which a length
    of at most `DAY - 1` cannot reach. Two meetings with the same start are
    a distance of zero apart, which any length exceeds.

    `sorted` builds a new list: the caller's is not this function's to
    reorder.
    """
    if not meetings:
        return True
    ordered = sorted((start, (end - start) % DAY) for start, end in meetings)
    following = [start for start, _ in ordered[1:]] + [ordered[0][0] + DAY]
    return all(
        start + length <= next_start
        for (start, length), next_start in zip(ordered, following, strict=True)
    )
