"""Reference solution. CI asserts this passes every test in `tests.py`."""


def find_peak(numbers: list[int]) -> int:
    """Return the largest value of a list that rises and then falls.

    Binary search on the slope. Comparing a value with the one after it says
    which side of the peak it is on: lower than the next means still
    climbing, so the peak is strictly to the right; higher means descending
    or at the top, so the peak is here or to the left.

    The invariant is that the peak is always within `low..high`. `middle` is
    always less than `high`, so `middle + 1` is always a real position, and
    the range shrinks every round until it is one value wide.
    """
    low, high = 0, len(numbers) - 1
    while low < high:
        middle = (low + high) // 2
        if numbers[middle] < numbers[middle + 1]:
            low = middle + 1
        else:
            high = middle
    return numbers[low]
