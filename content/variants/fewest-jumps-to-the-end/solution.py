"""Reference solution. CI asserts this passes every test in `tests.py`."""


def fewest_jumps(jumps: list[int]) -> int:
    """Return the fewest jumps from the first position to the last.

    A breadth-first search with the queue optimised away. The positions
    reachable in exactly `taken` jumps form a contiguous range ending at
    `edge`; scanning that range finds `furthest`, the end of the range one
    jump later. Reaching `edge` therefore costs one jump and moves the edge.

    If `furthest` has not moved past `edge` when the scan arrives there, no
    position in the layer can leave it, and the end is out of reach.
    """
    last = len(jumps) - 1
    taken = 0
    edge = 0
    furthest = 0
    for position in range(last):
        furthest = max(furthest, position + jumps[position])
        if position == edge:
            if furthest == edge:
                return -1
            taken += 1
            edge = furthest
            if edge >= last:
                break
    return taken
