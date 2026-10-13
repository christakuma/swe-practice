"""Reference solution. CI asserts this passes every test in `tests.py`."""

import heapq


def assign_rooms(meetings: list[tuple[int, int]]) -> list[int]:
    """Return the room each meeting is given.

    Two heaps, because there are two different orders in play. `busy` holds
    `(end, room)` for rooms in use and is ordered by when they empty. `free`
    holds the numbers of empty rooms and is ordered by number.

    Before each meeting is booked, every room whose meeting has ended by its
    start is moved from `busy` to `free` -- all of them, not just the first.
    Only then is the lowest free number taken. Popping one room from `busy`
    and reusing it directly gives the room that emptied *earliest*, which is
    a different room whenever two or more are empty.

    The meetings are visited by start time through a sorted list of
    positions, so the answer can be written back in input order and equal
    starts keep the order they were given in.
    """
    rooms = [0] * len(meetings)
    busy: list[tuple[int, int]] = []
    free: list[int] = []
    opened = 0
    for position in sorted(range(len(meetings)), key=lambda p: meetings[p][0]):
        start, end = meetings[position]
        while busy and busy[0][0] <= start:
            heapq.heappush(free, heapq.heappop(busy)[1])
        if free:
            room = heapq.heappop(free)
        else:
            room = opened
            opened += 1
        rooms[position] = room
        heapq.heappush(busy, (end, room))
    return rooms
