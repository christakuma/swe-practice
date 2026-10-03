"""Reference solution. CI asserts this passes every test in `tests.py`."""

from collections import defaultdict


def count_subarrays(numbers: list[int], target: int) -> int:
    """Count the contiguous slices of `numbers` that sum to `target`.

    The restatement that solves it: the sum of the slice ending at `index` and
    starting at `start` is `prefix[index] - prefix[start - 1]`. So a slice sums
    to `target` exactly when some earlier prefix sum equals
    `running - target` -- and counting those is a dict lookup rather than a
    search.

    Which turns "how many slices" into "how many times have I seen that earlier
    prefix", answered in one pass.

    `seen[0] = 1` before the loop is the part that looks like an off-by-one and
    is the whole base case: the empty prefix has sum zero, and without it every
    slice that starts at index 0 is missed. `[3], target 3` is the shortest input
    that proves it.

    Note what this does NOT do: slide a window. A window needs the sum to grow
    monotonically as the window widens, which negative numbers break -- and
    `[1, -1, 0], target 0` has three answers that no sliding window finds.
    """
    seen: dict[int, int] = defaultdict(int)
    seen[0] = 1

    running = 0
    found = 0
    for value in numbers:
        running += value
        found += seen[running - target]
        seen[running] += 1
    return found
