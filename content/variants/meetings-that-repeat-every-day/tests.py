"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import can_attend_all

DAY = 24 * 60


def minutes_of(meeting: tuple[int, int]) -> frozenset[int]:
    """Every minute of the day a meeting is in progress, marked one by one.

    A different idea from sorting and comparing neighbours, on purpose: it
    walks forward from the start until it arrives at the end, going round
    through midnight if that is where the end is, and knows nothing about
    lengths or order.
    """
    start, end = meeting
    marked = set()
    minute = start
    while minute != end:
        marked.add(minute)
        minute = (minute + 1) % DAY
    return frozenset(marked)


def test_meetings_inside_one_day_are_the_standard_problem() -> None:
    """Answers as the standard version does when nothing reaches midnight."""
    assert can_attend_all([(540, 600), (600, 660), (840, 900)]) is True
    assert can_attend_all([(540, 600), (570, 630)]) is False


def test_a_meeting_may_run_through_midnight() -> None:
    """Accepts a meeting that starts late and ends early the next morning."""
    assert can_attend_all([(1320, 120), (180, 240)]) is True


def test_a_late_meeting_clashes_with_an_early_one_the_next_morning() -> None:
    """Rejects an early meeting that last night's late one is still running in.

    Compared as written, 60 to 90 is nowhere near 1320 to 120.
    """
    assert can_attend_all([(1320, 120), (60, 90)]) is False
    assert can_attend_all([(60, 90), (1320, 120)]) is False


def test_a_late_meeting_clashes_with_one_later_the_same_evening() -> None:
    """Rejects a meeting that starts while one bound for midnight is running.

    The end of the first is 120, and 1380 is not before it. That comparison
    is the standard version's, and it is the wrong way round here.
    """
    assert can_attend_all([(1320, 120), (1380, 1400)]) is False


def test_the_last_meeting_of_the_day_is_followed_by_the_first() -> None:
    """Rejects a clash between the latest start and the earliest.

    In start order these two are the last and the first, which are neighbours
    on a clock and not in a list.
    """
    assert can_attend_all([(60, 120), (600, 660), (1400, 90)]) is False
    assert can_attend_all([(60, 120), (600, 660), (1400, 60)]) is True


def test_touching_at_midnight_is_not_overlapping() -> None:
    """Lets a meeting begin as another ends, on either side of midnight."""
    assert can_attend_all([(1380, 0), (0, 60)]) is True
    assert can_attend_all([(1320, 120), (120, 200)]) is True
    assert can_attend_all([(1320, 120), (119, 200)]) is False


def test_two_meetings_through_midnight_always_clash() -> None:
    """Rejects two meetings that are both in progress at midnight."""
    assert can_attend_all([(1320, 60), (1380, 30)]) is False


def test_meetings_that_start_together_clash() -> None:
    """Rejects two meetings with the same start, and two copies of one."""
    assert can_attend_all([(600, 660), (600, 630)]) is False
    assert can_attend_all([(600, 660), (600, 660)]) is False
    assert can_attend_all([(1320, 120), (1320, 120)]) is False


def test_a_meeting_can_last_almost_the_whole_day() -> None:
    """Handles a meeting one minute short of a day, and the minute it leaves."""
    assert can_attend_all([(600, 599)]) is True
    assert can_attend_all([(600, 599), (599, 600)]) is True
    assert can_attend_all([(600, 599), (0, 1)]) is False


def test_handles_no_meetings_and_one() -> None:
    """Accepts an empty diary, and any single meeting."""
    assert can_attend_all([]) is True
    assert can_attend_all([(0, 1)]) is True
    assert can_attend_all([(1439, 0)]) is True
    assert can_attend_all([(1320, 120)]) is True


def test_agrees_with_marking_every_minute() -> None:
    """Matches a minute-by-minute diary for every schedule of up to three.

    Times are drawn from both sides of midnight and the middle of the day, so
    the meetings are short ones, ones through midnight, and ones that last
    nearly all day.
    """
    times = (0, 1, 2, 720, 1438, 1439)
    choices = [(start, end) for start in times for end in times if start != end]
    overlap = {
        (first, second): not minutes_of(first).isdisjoint(minutes_of(second))
        for first in choices
        for second in choices
    }
    for size in range(4):
        for chosen in product(choices, repeat=size):
            expected = not any(overlap[pair] for pair in combinations(chosen, 2))
            assert can_attend_all(list(chosen)) is expected, chosen


def test_fills_every_minute_of_the_day() -> None:
    """Accepts 1,440 one-minute meetings, and rejects one more.

    The day is full, in no particular order, with the meeting at 23:59 ending
    at an `end` of 0. Any further meeting has to land on one of them.
    """
    full = [(minute, (minute + 1) % DAY) for minute in range(DAY)]
    shuffled = [full[(position * 577) % DAY] for position in range(DAY)]

    assert sorted(shuffled) == sorted(full)
    assert can_attend_all(shuffled) is True
    assert can_attend_all([*shuffled, (700, 701)]) is False
    assert can_attend_all([*shuffled[:-1], (1439, 1)]) is False


def test_leaves_the_list_alone() -> None:
    """Leaves the caller's list in its original order."""
    meetings = [(1320, 120), (600, 660), (180, 240)]

    can_attend_all(meetings)

    assert meetings == [(1320, 120), (600, 660), (180, 240)]
