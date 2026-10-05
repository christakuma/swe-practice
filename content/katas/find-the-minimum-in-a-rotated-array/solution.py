"""Reference solution. CI asserts this passes every test in `tests.py`."""


def find_minimum(numbers: list[int]) -> int:
    """Return the smallest value in a rotated sorted list of distinct integers.

    A rotation leaves two sorted runs back to back, with every value in the
    left run larger than every value in the right one. The minimum is the first
    element of the right run -- the single place where the list steps down.

    Binary search needs one question answered at each step: *which run is the
    middle element in?* Comparing it with the **last** element settles that.
    If `numbers[mid] > numbers[high]`, the middle sits in the left run, so the
    step-down is strictly to its right. Otherwise the middle is already in the
    right run and may itself be the minimum.

    Comparing with `numbers[low]` instead does not work on an unrotated list,
    where the middle is both in "the left run" and not greater than anything to
    its right -- the last element is the only comparand that distinguishes the
    two cases without a separate check for rotation zero.

    **The two branches are deliberately asymmetric.** `low = mid + 1` discards
    the middle, which is safe because it has been proven not to be the minimum.
    `high = mid` keeps it, because it might be. Writing `high = mid - 1` for
    symmetry steps over the answer; writing `low = mid` in the other branch
    makes no progress when `low` and `high` are adjacent and the loop hangs.

    `low < high` rather than `low <= high`: the loop runs until the window is
    one wide, and that single remaining element is the answer. There is no
    "not found" case, so nothing needs to be returned from inside the loop.
    """
    low, high = 0, len(numbers) - 1
    while low < high:
        mid = (low + high) // 2
        if numbers[mid] > numbers[high]:
            low = mid + 1
        else:
            high = mid
    return numbers[low]
