"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import rooms_needed


def peak(meetings: list[tuple[int, int]], gap: int) -> int:
    """The most rooms tied up at any start time, with each held for the gap."""
    return max(
        (sum(a <= start < b + gap for a, b in meetings) for start, _ in meetings),
        default=0,
    )


def test_matches_the_standard_problem_with_no_gap() -> None:
    """Gives the standard answers when the gap is zero."""
    assert rooms_needed([(0, 30), (5, 10), (15, 20)], 0) == 2
    assert rooms_needed([(1, 2), (2, 3)], 0) == 1


def test_a_gap_keeps_back_to_back_meetings_apart() -> None:
    """Needs a second room when the first is still being cleaned."""
    assert rooms_needed([(1, 2), (2, 3)], 1) == 2


def test_a_room_is_ready_exactly_when_the_gap_has_passed() -> None:
    """Reuses a room for a meeting that starts just as cleaning ends."""
    assert rooms_needed([(0, 10), (12, 20)], 2) == 1
    assert rooms_needed([(0, 10), (11, 20)], 2) == 2


def test_handles_a_mixed_schedule() -> None:
    """Reuses the rooms that are ready and opens one for the meeting that is early."""
    assert rooms_needed([(0, 10), (12, 20), (11, 15)], 2) == 2


def test_needs_no_rooms_for_no_meetings() -> None:
    """Returns 0 for no meetings, whatever the gap."""
    assert rooms_needed([], 5) == 0


def test_agrees_with_counting_the_peak() -> None:
    """Matches a direct count of the busiest moment for every small schedule."""
    choices = [(start, end) for start in range(5) for end in range(start + 1, 5)]
    for size in range(4):
        for chosen in product(choices, repeat=size):
            meetings = list(chosen)
            for gap in range(3):
                assert rooms_needed(meetings, gap) == peak(meetings, gap), (
                    meetings,
                    gap,
                )


def test_leaves_the_list_alone() -> None:
    """Leaves the caller's list in its original order."""
    meetings = [(5, 6), (1, 2)]

    rooms_needed(meetings, 1)

    assert meetings == [(5, 6), (1, 2)]


def test_handles_two_hundred_thousand_meetings() -> None:
    """Handles two hundred thousand meetings within the time limit."""
    meetings = [(2 * index, 2 * index + 2) for index in reversed(range(200_000))]

    assert rooms_needed(meetings, 0) == 1
    assert rooms_needed(meetings, 1) == 2
