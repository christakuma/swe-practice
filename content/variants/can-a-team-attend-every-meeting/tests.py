"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import can_attend_all


def peak(meetings: list[tuple[int, int]]) -> int:
    """The most meetings in progress at any start time, counted directly."""
    return max(
        (sum(a <= start < b for a, b in meetings) for start, _ in meetings), default=0
    )


def test_two_people_cover_what_one_cannot() -> None:
    """Accepts a schedule that needs exactly as many people as there are."""
    meetings = [(0, 30), (5, 10), (15, 20)]

    assert can_attend_all(meetings, 2) is True
    assert can_attend_all(meetings, 1) is False


def test_three_at_once_need_three() -> None:
    """Rejects a moment with more meetings than people."""
    assert can_attend_all([(1, 4), (2, 5), (3, 6)], 2) is False
    assert can_attend_all([(1, 4), (2, 5), (3, 6)], 3) is True


def test_touching_meetings_share_a_person() -> None:
    """Lets one person take a meeting that starts as another ends."""
    assert can_attend_all([(1, 2), (2, 3), (3, 4)], 1) is True


def test_handles_nobody_and_nothing() -> None:
    """Needs nobody for no meetings, and somebody for any meeting."""
    assert can_attend_all([], 0) is True
    assert can_attend_all([(1, 2)], 0) is False


def test_agrees_with_counting_the_peak() -> None:
    """Matches a direct count of the busiest moment for every small schedule."""
    choices = [(start, end) for start in range(4) for end in range(start + 1, 4)]
    for size in range(5):
        for chosen in product(choices, repeat=size):
            meetings = list(chosen)
            for people in range(5):
                expected = peak(meetings) <= people
                assert can_attend_all(meetings, people) is expected, (meetings, people)


def test_leaves_the_list_alone() -> None:
    """Leaves the caller's list in its original order."""
    meetings = [(5, 6), (1, 2)]

    can_attend_all(meetings, 1)

    assert meetings == [(5, 6), (1, 2)]


def test_checks_a_hundred_thousand_meetings() -> None:
    """Handles a hundred thousand meetings within the time limit."""
    meetings = [(index, index + 2) for index in reversed(range(100_000))]

    assert can_attend_all(meetings, 2) is True
    assert can_attend_all(meetings, 1) is False
