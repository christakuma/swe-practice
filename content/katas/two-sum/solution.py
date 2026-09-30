"""Reference solution. CI asserts this passes every test in `tests.py`."""


def two_sum(numbers: list[int], target: int) -> tuple[int, int]:
    """Return the two positions whose values add up to `target`.

    One pass, one dict. The insight is that standing on `value`, the number that
    would complete the pair is not something to search for -- it is
    `target - value`, and the only question is whether it has already gone past.

    Checking `seen` *before* inserting the current index is what makes this
    correct rather than merely fast: it is why an element cannot pair with
    itself, and why `[3, 3]` resolves to `(0, 1)` instead of `(1, 1)`.
    """
    seen: dict[int, int] = {}
    for index, value in enumerate(numbers):
        complement = target - value
        if complement in seen:
            return (seen[complement], index)
        seen[value] = index
    raise ValueError("no pair of values adds up to the target")
