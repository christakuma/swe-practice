"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations_with_replacement

from solution import rooms_needed


def reference(meetings: list[tuple[int, int]]) -> int:
    """Peak overlap by sampling every start instant -- an independent oracle.

    The count can only peak at a moment some meeting begins, so checking each
    start is sufficient. It does no sorting and no sweeping, so it shares
    nothing with the intended solution.
    """
    best = 0
    for moment, _ in meetings:
        best = max(best, sum(1 for start, end in meetings if start <= moment < end))
    return best


def test_handles_the_worked_example() -> None:
    """Returns two rooms for the documented meetings."""
    assert rooms_needed([(0, 30), (5, 10), (15, 20)]) == 2


def test_handles_non_overlapping_meetings() -> None:
    """Returns one room when nothing overlaps."""
    assert rooms_needed([(7, 10), (2, 4)]) == 1
    assert rooms_needed([(1, 2), (3, 4), (5, 6)]) == 1


def test_handles_an_empty_list() -> None:
    """Returns 0 when there are no meetings."""
    assert rooms_needed([]) == 0


def test_handles_a_single_meeting() -> None:
    """Returns one room for one meeting."""
    assert rooms_needed([(1, 5)]) == 1


def test_counts_identical_meetings_separately() -> None:
    """Needs one room per meeting when they all coincide."""
    assert rooms_needed([(1, 5), (1, 5), (1, 5)]) == 3
    assert rooms_needed([(1, 5), (1, 5)]) == 2


def test_shares_a_room_between_touching_meetings() -> None:
    """Does not need a second room when one ends as another starts.

    The discriminating case for the tie-break: at an equal timestamp the
    ending must be processed before the start. A solution using a strict
    comparison counts these as overlapping and reports 2.
    """
    assert rooms_needed([(1, 2), (2, 3)]) == 1
    assert rooms_needed([(1, 2), (2, 3), (3, 4), (4, 5)]) == 1


def test_handles_a_meeting_containing_others() -> None:
    """Counts a long meeting against each short one inside it."""
    assert rooms_needed([(0, 100), (10, 20), (30, 40)]) == 2
    assert rooms_needed([(0, 100), (10, 20), (15, 25)]) == 3


def test_finds_the_peak_not_the_total() -> None:
    """Returns the maximum simultaneous count, not the number of overlaps.

    Four meetings in two disjoint pairs: the peak is 2, even though two
    separate overlaps exist. A solution counting overlapping pairs reports 2
    here by luck and 3 for three pairs.
    """
    assert rooms_needed([(1, 5), (2, 6), (10, 15), (11, 16)]) == 2
    assert rooms_needed([(1, 5), (2, 6), (10, 15), (11, 16), (20, 25), (21, 26)]) == 2


def test_handles_a_staircase() -> None:
    """Handles meetings that each overlap only their neighbour."""
    assert rooms_needed([(1, 3), (2, 4), (3, 5), (4, 6)]) == 2


def test_handles_unsorted_input() -> None:
    """Gives the same answer however the meetings are ordered."""
    meetings = [(15, 20), (0, 30), (5, 10)]

    assert rooms_needed(meetings) == 2
    assert rooms_needed(list(reversed(meetings))) == 2


def test_handles_negative_times() -> None:
    """Handles timestamps below zero."""
    assert rooms_needed([(-10, -5), (-7, -1)]) == 2
    assert rooms_needed([(-10, -5), (-5, 0)]) == 1


def test_returns_a_plain_integer() -> None:
    """Returns an int rather than a bool."""
    assert type(rooms_needed([(1, 2)])) is int


def test_does_not_mutate_the_input() -> None:
    """Leaves the caller's list in its original order."""
    meetings = [(15, 20), (0, 30), (5, 10)]
    before = list(meetings)

    rooms_needed(meetings)

    assert meetings == before


def test_agrees_with_a_sampling_oracle_on_every_small_input() -> None:
    """Matches the peak-overlap oracle for every small meeting list.

    Every multiset of up to four meetings over a small time range -- about four
    thousand cases. The tie-break at equal timestamps is the only subtle part
    and it fails only when a start and an end coincide.
    """
    pool = [(start, end) for start in range(5) for end in range(start + 1, 6)]
    for size in range(5):
        for chosen in combinations_with_replacement(pool, size):
            meetings = list(chosen)

            assert rooms_needed(meetings) == reference(meetings), meetings


def test_handles_many_nested_meetings() -> None:
    """Needs a room per meeting when all of them nest.

    Each meeting contains the next, so every one of them is running at the
    innermost moment.
    """
    size = 2_000
    meetings = [(value, 2 * size - value) for value in range(size)]

    assert rooms_needed(meetings) == size


def test_handles_a_large_input() -> None:
    """Handles two hundred thousand meetings within the time limit.

    Laid out end to end so they all share one room, which is the case where a
    solution that re-scans the list per meeting is quadratic.
    """
    meetings = [(value, value + 1) for value in range(200_000)]

    assert rooms_needed(meetings) == 1
