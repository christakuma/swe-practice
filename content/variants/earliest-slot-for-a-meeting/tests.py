"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations_with_replacement

from solution import earliest_slot


def by_trying_every_minute(
    meetings: list[tuple[int, int]], duration: int, opens: int, closes: int
) -> int | None:
    """The answer by testing each start time in turn. An oracle for small days."""
    for candidate in range(opens, closes - duration + 1):
        if all(
            candidate >= end or candidate + duration <= start for start, end in meetings
        ):
            return candidate
    return None


def test_finds_a_gap_between_two_meetings() -> None:
    """Returns the end of the meeting before the first gap that is long enough."""
    assert earliest_slot([(9, 10), (12, 13)], 2, 8, 17) == 10


def test_an_empty_diary_starts_when_the_day_does() -> None:
    """Returns the opening time when there are no meetings."""
    assert earliest_slot([], 3, 5, 8) == 5
    assert earliest_slot([], 1, -4, 9) == -4


def test_uses_the_gap_before_the_first_meeting() -> None:
    """Returns the opening time when the first meeting starts late enough."""
    assert earliest_slot([(10, 12)], 2, 8, 17) == 8
    assert earliest_slot([(10, 12)], 3, 8, 17) == 12


def test_uses_the_gap_after_the_last_meeting() -> None:
    """Returns the end of the last meeting when nothing earlier fits."""
    assert earliest_slot([(8, 11), (11, 15)], 2, 8, 17) == 15
    assert earliest_slot([(8, 16)], 1, 8, 17) == 16


def test_returns_none_when_the_day_is_full() -> None:
    """Returns None when no gap is long enough."""
    assert earliest_slot([(8, 12), (12, 17)], 1, 8, 17) is None
    assert earliest_slot([(9, 10), (12, 13)], 5, 8, 17) is None
    assert earliest_slot([], 4, 5, 8) is None


def test_a_slot_may_touch_its_neighbours() -> None:
    """Accepts a gap exactly as long as the meeting.

    Half-open intervals: starting when one meeting ends and ending when the
    next starts overlaps neither.
    """
    assert earliest_slot([(8, 10), (13, 17)], 3, 8, 17) == 10
    assert earliest_slot([(8, 10), (13, 17)], 4, 8, 17) is None


def test_a_slot_may_end_exactly_at_closing_time() -> None:
    """Accepts a meeting that finishes as the day does, and nothing later."""
    assert earliest_slot([(8, 15)], 2, 8, 17) == 15
    assert earliest_slot([(8, 15)], 3, 8, 17) is None
    assert earliest_slot([], 9, 8, 17) == 8


def test_a_meeting_inside_another_does_not_free_the_diary_early() -> None:
    """Waits for the longer meeting when a shorter one inside it ends first."""
    assert earliest_slot([(9, 12), (10, 11)], 1, 9, 17) == 12
    assert earliest_slot([(8, 14), (9, 10), (11, 12)], 2, 8, 17) == 14


def test_overlapping_meetings_leave_no_gap_between_them() -> None:
    """Treats meetings that overlap as one busy stretch."""
    assert earliest_slot([(8, 11), (10, 13), (12, 15)], 1, 8, 17) == 15


def test_meetings_arrive_in_any_order() -> None:
    """Finds the earliest gap whatever order the meetings are listed in."""
    assert earliest_slot([(14, 15), (8, 9), (11, 12)], 2, 8, 17) == 9
    assert earliest_slot([(12, 13), (9, 10)], 2, 8, 17) == 10


def test_meetings_before_the_day_opens_do_not_count() -> None:
    """Ignores meetings that are over before the day begins."""
    assert earliest_slot([(1, 3), (4, 6)], 2, 8, 17) == 8
    assert earliest_slot([(1, 8)], 2, 8, 17) == 8


def test_a_meeting_running_into_the_day_delays_the_start() -> None:
    """Starts after a meeting that began before opening time and is still going."""
    assert earliest_slot([(6, 10)], 2, 8, 17) == 10
    assert earliest_slot([(6, 10), (7, 9)], 2, 8, 17) == 10


def test_a_gap_that_starts_before_the_day_is_measured_from_opening() -> None:
    """Does not count time before the day opens towards a gap.

    The diary is free from 5 to 9, but only the hour from 8 is usable.
    """
    assert earliest_slot([(3, 5), (9, 12)], 2, 8, 17) == 12
    assert earliest_slot([(9, 12)], 2, 8, 17) == 12


def test_meetings_after_the_day_closes_do_not_count() -> None:
    """Ignores meetings that begin after closing time."""
    assert earliest_slot([(8, 16), (20, 22)], 2, 8, 17) is None
    assert earliest_slot([(8, 14), (20, 22)], 2, 8, 17) == 14


def test_a_gap_that_runs_past_closing_is_cut_off_there() -> None:
    """Does not use a gap that is long enough only by running past the day's end."""
    assert earliest_slot([(8, 16), (19, 22)], 3, 8, 17) is None


def test_leaves_the_diary_as_it_was() -> None:
    """Does not sort or otherwise change the list it was given."""
    meetings = [(14, 15), (8, 9), (11, 12)]

    earliest_slot(meetings, 1, 8, 17)

    assert meetings == [(14, 15), (8, 9), (11, 12)]


def test_agrees_with_trying_every_start_time() -> None:
    """Matches a minute-by-minute search on every small diary.

    Every set of up to three meetings with whole-number times from 0 to 6,
    repeats included, against three working days and three durations.
    """
    slots = [(start, end) for start in range(7) for end in range(start + 1, 7)]
    for count in range(4):
        for chosen in combinations_with_replacement(slots, count):
            meetings = list(reversed(chosen))
            for opens, closes in ((0, 6), (1, 5), (2, 7)):
                for duration in (1, 2, 3):
                    expected = by_trying_every_minute(meetings, duration, opens, closes)

                    assert (
                        earliest_slot(meetings, duration, opens, closes) == expected
                    ), (
                        meetings,
                        duration,
                        opens,
                        closes,
                    )


def test_handles_a_hundred_thousand_meetings() -> None:
    """Searches a diary of a hundred thousand meetings.

    Meetings of nine minutes start every ten, so every gap is one minute
    long -- except that one meeting is missing, three quarters of the way
    through, which leaves a gap of eleven.
    """
    count = 100_000
    missing = 75_000
    meetings = [(10 * slot, 10 * slot + 9) for slot in range(count) if slot != missing]
    meetings.reverse()

    assert earliest_slot(meetings, 1, 0, 10 * count) == 9
    assert earliest_slot(meetings, 5, 0, 10 * count) == 10 * missing - 1
    assert earliest_slot(meetings, 12, 0, 10 * count) is None
