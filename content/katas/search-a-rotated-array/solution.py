"""Reference solution. CI asserts this passes every test in `tests.py`."""


def search(numbers: list[int], target: int) -> int:
    """Return the index of `target` in a rotated sorted list, or -1.

    The observation that makes one pass possible: wherever you cut, **at least
    one half is fully sorted**, because there is only one rotation point and it
    can fall in only one half. So each step has two jobs -- work out which half
    is the clean one, then decide whether the target lives in it.

    Deciding is two comparisons, because membership in a sorted run is just
    "does it fall between the endpoints". If it does, keep that half; if not,
    keep the other. Either way one half is discarded, so the search stays
    logarithmic.

    The body is written as *decide, then act* rather than as four nested
    branches each with its own window update. The nested form duplicates
    `high = mid - 1` and `low = mid + 1` twice over, and the duplicates are
    where sign errors hide; naming the decision once means there is exactly one
    place each window update happens.

    `numbers[low] <= numbers[mid]` has to be `<=` and not `<`. When the window
    is two elements wide, `mid` rounds down to `low` and they are the same
    element -- a strict comparison then calls the left half unsorted, which is
    false, and the search discards the half holding the answer. This is the
    most common way to get this kata almost right: it passes every odd-sized
    case picked by hand.

    `low <= high`, and a return from inside the loop -- unlike
    `find-the-minimum-in-a-rotated-array`. This search has a "not found"
    answer, so the window has to be allowed to close completely, and -1 is
    what falling out of the loop means.
    """
    low, high = 0, len(numbers) - 1
    while low <= high:
        mid = (low + high) // 2
        if numbers[mid] == target:
            return mid

        if numbers[low] <= numbers[mid]:
            # The left half is sorted, so the target is in it only if it lies
            # between its endpoints.
            keep_left = numbers[low] <= target < numbers[mid]
        else:
            # Otherwise the right half is the sorted one, and the left half is
            # where the target must be if it is not in that range.
            keep_left = not numbers[mid] < target <= numbers[high]

        if keep_left:
            high = mid - 1
        else:
            low = mid + 1
    return -1
