"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import rooms_needed


def test_counts_two_rooms_for_an_overlap() -> None:
    """Needs a second room while two meetings overlap."""
    assert rooms_needed([(0, 30), (5, 10), (15, 20)]) == 2


def test_needs_one_room_for_meetings_in_sequence() -> None:
    """Reuses the room for meetings that do not overlap."""
    assert rooms_needed([(7, 10), (2, 4)]) == 1


def test_treats_touching_meetings_as_compatible() -> None:
    """Shares a room when one meeting ends exactly as the next begins.

    The intervals are half-open, so 3 belongs to the meeting starting at 3 and
    not to the one ending there. With `<` instead of `<=` this needs three
    rooms.
    """
    assert rooms_needed([(1, 2), (2, 3), (3, 4)]) == 1


def test_counts_three_overlapping_meetings() -> None:
    """Needs a room per meeting when all three overlap."""
    assert rooms_needed([(1, 4), (2, 5), (3, 6)]) == 3


def test_reuses_a_room_several_times_under_a_long_meeting() -> None:
    """Needs only two rooms when short meetings queue under a long one."""
    assert rooms_needed([(1, 10), (2, 3), (4, 5), (6, 7)]) == 2


def test_does_not_depend_on_the_input_order() -> None:
    """Gives the same answer for unsorted input."""
    assert rooms_needed([(1, 3), (3, 5), (2, 4)]) == 2


def test_handles_a_single_meeting() -> None:
    """Needs one room for one meeting."""
    assert rooms_needed([(1, 5)]) == 1


def test_handles_no_meetings() -> None:
    """Needs no rooms for no meetings."""
    assert rooms_needed([]) == 0


def test_handles_many_sequential_meetings_quickly() -> None:
    """Keeps one room for twenty thousand back-to-back meetings.

    Each ends exactly as the next starts, so one room suffices. A solution
    comparing every pair of meetings is two hundred million comparisons.
    """
    meetings = [(index, index + 1) for index in range(20_000)]

    assert rooms_needed(meetings) == 1


def test_handles_many_overlapping_meetings_quickly() -> None:
    """Opens a room per meeting when two thousand all overlap.

    Every meeting starts at 0, so the heap grows to two thousand entries and
    never reuses anything.
    """
    meetings = [(0, index + 1) for index in range(2_000)]

    assert rooms_needed(meetings) == 2_000
