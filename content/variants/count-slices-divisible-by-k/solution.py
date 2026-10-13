"""Reference solution. CI asserts this passes every test in `tests.py`."""


def count_subarrays(numbers: list[int], k: int) -> int:
    """Count the contiguous slices of `numbers` whose sum is divisible by `k`.

    A slice's sum is the difference of two running totals, and that
    difference is a multiple of `k` exactly when the two totals leave the
    same remainder. So each new total contributes one slice for every earlier
    total with its remainder.

    Python's `%` already returns a remainder in `0..k - 1` for a negative
    total, which is what makes negative values need no special handling
    here; in most other languages this line needs a correction.
    """
    seen = {0: 1}
    total = 0
    count = 0
    for value in numbers:
        total += value
        remainder = total % k
        count += seen.get(remainder, 0)
        seen[remainder] = seen.get(remainder, 0) + 1
    return count
