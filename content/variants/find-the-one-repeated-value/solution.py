"""Reference solution. CI asserts this passes every test in `tests.py`."""


def find_duplicate(numbers: list[int]) -> int:
    """Return the one value that appears more than once.

    Read the list as a linked list: position `i` points at position
    `numbers[i]`. Every value is at least 1, so nothing points at position 0
    and the walk from 0 starts on a tail. Two positions holding the same
    value are two arrows into one position -- the place where the tail joins
    a loop -- and that position's index *is* the repeated value.

    So this is "where does the cycle begin?": advance a slow and a fast
    pointer until they meet inside the loop, then walk one pointer from the
    start and one from the meeting point in step. They meet at the entrance.
    Three integers of state, and the list is only ever read.
    """
    slow = numbers[0]
    fast = numbers[numbers[0]]
    while slow != fast:
        slow = numbers[slow]
        fast = numbers[numbers[fast]]

    probe = 0
    while probe != slow:
        probe = numbers[probe]
        slow = numbers[slow]
    return probe
