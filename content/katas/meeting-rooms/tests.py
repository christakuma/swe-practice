"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import can_attend_all


def clashes(meetings: list[tuple[int, int]]) -> bool:
    """The definition, with no sorting in it: does any pair overlap?

    Two half-open intervals overlap exactly when each starts before the other
    ends. Quadratic, and deliberately a different idea from the solution, so
    the sweep below is a comparison against the rule rather than against a
    second copy of the same trick.
    """
    return any(a[0] < b[1] and b[0] < a[1] for a, b in combinations(meetings, 2))


def test_reports_a_clash() -> None:
    """Returns False when one meeting runs through two others."""
    assert can_attend_all([(0, 30), (5, 10), (15, 20)]) is False


def test_accepts_meetings_that_do_not_overlap() -> None:
    """Returns True when the meetings are all apart."""
    assert can_attend_all([(7, 10), (2, 4)]) is True


def test_touching_meetings_do_not_clash() -> None:
    """Accepts a meeting that starts exactly when another ends."""
    assert can_attend_all([(1, 2), (2, 3), (3, 4)]) is True


def test_an_overlap_of_one_unit_is_a_clash() -> None:
    """Rejects meetings that share even one unit of time."""
    assert can_attend_all([(1, 3), (2, 4)]) is False


def test_handles_no_meetings_and_one_meeting() -> None:
    """Returns True when there is nothing to clash with."""
    assert can_attend_all([]) is True
    assert can_attend_all([(5, 8)]) is True


def test_the_same_slot_twice_is_a_clash() -> None:
    """Rejects two meetings booked into the same slot."""
    assert can_attend_all([(1, 5), (1, 5)]) is False


def test_a_meeting_inside_another_is_a_clash() -> None:
    """Rejects a short meeting held during a long one."""
    assert can_attend_all([(1, 10), (4, 5)]) is False


def test_finds_a_clash_between_meetings_far_apart_in_the_input() -> None:
    """Finds a clash however the meetings are ordered.

    The two that overlap are first and last in the list, with compatible
    meetings between them. A solution that compares neighbours *in the order
    given*, without sorting, sees four harmless pairs and returns True.
    """
    assert can_attend_all([(10, 20), (0, 5), (30, 40), (50, 60), (15, 25)]) is False


def test_handles_times_below_zero() -> None:
    """Handles timestamps below zero."""
    assert can_attend_all([(-10, -5), (-5, 0), (0, 3)]) is True
    assert can_attend_all([(-10, -4), (-5, 0)]) is False


def test_returns_a_bool() -> None:
    """Returns True or False rather than a truthy value."""
    assert can_attend_all([(1, 2)]) is True
    assert can_attend_all([(1, 3), (2, 4)]) is False


def test_leaves_the_list_alone() -> None:
    """Leaves the caller's list in its original order."""
    meetings = [(5, 6), (1, 2), (3, 4)]

    can_attend_all(meetings)

    assert meetings == [(5, 6), (1, 2), (3, 4)]


def test_agrees_with_the_definition_for_every_small_schedule() -> None:
    """Matches the every-pair definition for every small set of meetings.

    Every interval with endpoints in 0..4, taken one, two and three at a time
    in every order: 10 + 100 + 1000 schedules. Touching, nesting, identical
    and disjoint pairs are all in there, in both orders.
    """
    intervals = [(start, end) for start in range(5) for end in range(start + 1, 5)]
    for size in (1, 2, 3):
        for schedule in product(intervals, repeat=size):
            meetings = list(schedule)
            assert can_attend_all(meetings) is not clashes(meetings), meetings


def test_checks_a_hundred_thousand_meetings() -> None:
    """Handles a hundred thousand meetings within the time limit.

    Back-to-back meetings handed over in reverse, so nothing clashes and the
    input is as far from sorted as it can be. Comparing every pair is five
    billion comparisons; sorting and one pass is not. Then the same schedule
    with one meeting stretched by a unit, which must be noticed.
    """
    count = 100_000
    meetings = [(2 * index, 2 * index + 2) for index in reversed(range(count))]

    assert can_attend_all(meetings) is True

    meetings[count // 2] = (meetings[count // 2][0], meetings[count // 2][1] + 1)

    assert can_attend_all(meetings) is False
