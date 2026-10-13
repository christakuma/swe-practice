"""Reference solution. CI asserts this passes every test in `tests.py`."""


def count_triples(numbers: list[int], target: int) -> int:
    """Count the triples of positions whose values sum to less than `target`.

    The two-pointer sweep from three-sum, with one change that is the whole
    problem: when the sum is small enough, the pointers have found not one
    triple but a block of them.

    With the list sorted and `first` fixed, suppose
    `ordered[first] + ordered[low] + ordered[high]` is below the target.
    Every position between `low` and `high` holds a value no larger than
    `ordered[high]`, so pairing `low` with any of them is below the target
    too. That is `high - low` triples, counted with one subtraction. `low`
    is then finished -- every partner it could have has been counted -- and
    moves up.

    If the sum is not small enough, `high` is too large for this `low` and
    for every later one, and moves down.

    Sorting a copy is safe because the question is about how many sets of
    positions qualify, and a permutation of the list has the same number.
    Nothing here skips repeated values: unlike three-sum, equal values at
    different positions are different choices and all of them count.
    """
    ordered = sorted(numbers)
    count = 0
    for first in range(len(ordered) - 2):
        low, high = first + 1, len(ordered) - 1
        while low < high:
            if ordered[first] + ordered[low] + ordered[high] < target:
                count += high - low
                low += 1
            else:
                high -= 1
    return count
