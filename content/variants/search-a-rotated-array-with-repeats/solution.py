"""Reference solution. CI asserts this passes every test in `tests.py`."""


def contains(numbers: list[int], target: int) -> bool:
    """Return whether `target` is in a rotated, non-decreasing list.

    The standard rotated search, plus one case. Normally one half of the
    window is sorted and comparing its ends says which: then the target is
    either inside that half's range or it is in the other half.

    With repeats, `numbers[low] == numbers[mid] == numbers[high]` gives no
    such information -- the rotation point could be on either side. Neither
    end is the target, because they equal the middle and the middle was just
    checked, so both are dropped and the search continues. That step is what
    makes the worst case linear, and it cannot be avoided: a list of equal
    values hiding one different one has to be looked through.
    """
    low, high = 0, len(numbers) - 1
    while low <= high:
        mid = (low + high) // 2
        if numbers[mid] == target:
            return True
        if numbers[low] == numbers[mid] == numbers[high]:
            low += 1
            high -= 1
        elif numbers[low] <= numbers[mid]:
            if numbers[low] <= target < numbers[mid]:
                high = mid - 1
            else:
                low = mid + 1
        elif numbers[mid] < target <= numbers[high]:
            low = mid + 1
        else:
            high = mid - 1
    return False
