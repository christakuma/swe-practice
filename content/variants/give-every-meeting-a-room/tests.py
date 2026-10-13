"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import assign_rooms

type Meeting = tuple[int, int]


def by_scanning_rooms(meetings: list[Meeting]) -> list[int]:
    """Book each meeting by trying room 0, then 1, then 2, until one is free."""
    free_from: list[int] = []
    rooms = [0] * len(meetings)
    order = sorted(range(len(meetings)), key=lambda p: (meetings[p][0], p))
    for position in order:
        start, end = meetings[position]
        empty = [room for room, available in enumerate(free_from) if available <= start]
        room = empty[0] if empty else len(free_from)
        if not empty:
            free_from.append(end)
        free_from[room] = end
        rooms[position] = room
    return rooms


def test_reuses_a_room_once_it_is_empty() -> None:
    """Gives a later meeting a room that an earlier one has left."""
    assert assign_rooms([(0, 30), (5, 10), (15, 20)]) == [0, 1, 1]


def test_opens_a_new_room_only_when_none_is_free() -> None:
    """Opens rooms in order, one for each meeting that overlaps all the others."""
    assert assign_rooms([(0, 5), (1, 6), (2, 7)]) == [0, 1, 2]
    assert assign_rooms([(0, 1), (2, 3), (4, 5)]) == [0, 0, 0]


def test_a_meeting_that_ends_as_another_starts_frees_its_room() -> None:
    """Hands a room over at the instant its meeting ends."""
    assert assign_rooms([(1, 2), (2, 3)]) == [0, 0]
    assert assign_rooms([(0, 5), (0, 2), (2, 4)]) == [0, 1, 1]


def test_takes_the_lowest_free_room_not_the_first_to_empty() -> None:
    """Chooses by room number when several rooms have emptied.

    Room 2 empties at 3 and room 1 at 4. A meeting starting at 5 finds both
    empty and takes room 1, although room 2 has been free for longer.
    """
    assert assign_rooms([(0, 10), (1, 4), (2, 3), (5, 6)]) == [0, 1, 2, 1]
    assert assign_rooms([(0, 9), (0, 8), (0, 1), (2, 3), (9, 10)]) == [0, 1, 2, 2, 0]


def test_goes_back_to_room_zero_when_it_is_free() -> None:
    """Returns to room 0 after it empties, even with higher rooms still in use."""
    assert assign_rooms([(0, 2), (1, 9), (3, 4)]) == [0, 1, 0]


def test_answers_in_the_order_the_meetings_were_given() -> None:
    """Books by start time and reports by position in the input."""
    assert assign_rooms([(4, 6), (1, 2), (2, 4)]) == [0, 0, 0]
    assert assign_rooms([(5, 8), (0, 6)]) == [1, 0]
    assert assign_rooms([(2, 9), (1, 9), (0, 9)]) == [2, 1, 0]


def test_equal_starts_are_booked_in_input_order() -> None:
    """Gives the lower room to the earlier of two meetings with the same start."""
    assert assign_rooms([(1, 5), (1, 2), (1, 9)]) == [0, 1, 2]
    assert assign_rooms([(1, 2), (1, 2)]) == [0, 1]


def test_handles_none_and_one() -> None:
    """Returns no rooms for no meetings and room 0 for one."""
    assert assign_rooms([]) == []
    assert assign_rooms([(-5, 5)]) == [0]


def test_handles_negative_times() -> None:
    """Handles meetings before time zero."""
    assert assign_rooms([(-10, -5), (-7, -1), (-5, 0)]) == [0, 1, 0]


def test_uses_exactly_as_many_rooms_as_ever_overlap() -> None:
    """Opens no more rooms than the largest number of meetings running at once."""
    meetings = [(0, 4), (1, 5), (2, 6), (4, 8), (5, 9), (6, 10), (9, 12)]

    rooms = assign_rooms(meetings)

    assert max(rooms) + 1 == 3
    for (a, room_a), (b, room_b) in combinations(zip(meetings, rooms, strict=True), 2):
        if room_a == room_b:
            assert a[1] <= b[0] or b[1] <= a[0], (a, b)


def test_agrees_with_scanning_the_rooms() -> None:
    """Matches a room-by-room scan for every short list of meetings.

    Every list of up to four meetings with times in 0..4.
    """
    shapes = list(combinations(range(5), 2))
    for size in range(1, 5):
        for chosen in product(shapes, repeat=size):
            meetings = list(chosen)
            assert assign_rooms(meetings) == by_scanning_rooms(meetings), meetings


def test_leaves_the_list_alone() -> None:
    """Does not reorder or modify the list it was given."""
    meetings = [(3, 4), (1, 2)]

    assign_rooms(meetings)

    assert meetings == [(3, 4), (1, 2)]


def test_handles_a_hundred_thousand_meetings() -> None:
    """Books 100,000 meetings within the time limit.

    Meeting i runs from i to i + 1000, so a thousand rooms fill up and are
    then reused in rotation: meeting i always gets room i mod 1000. Trying
    the rooms one by one for every meeting is fifty million steps.
    """
    count = 100_000
    meetings = [(start, start + 1000) for start in range(count)]

    assert assign_rooms(meetings) == [start % 1000 for start in range(count)]
