"""Reference solution. CI asserts this passes every test in `tests.py`."""


def find_minimum(numbers: list[int]) -> int:
    """Return the smallest value in a rotated, non-decreasing list.

    Compare the middle with the right-hand end. Larger: the rotation point,
    and so the minimum, is to the right of the middle. Smaller: the middle
    could be the minimum, and nothing to its right is.

    Equal is the case repeats add, and it says nothing about direction. But
    the right-hand value is safe to discard, because the middle holds a copy
    of it -- so the window shrinks by one and the comparison is tried again.
    """
    low, high = 0, len(numbers) - 1
    while low < high:
        mid = (low + high) // 2
        if numbers[mid] > numbers[high]:
            low = mid + 1
        elif numbers[mid] < numbers[high]:
            high = mid
        else:
            high -= 1
    return numbers[low]
