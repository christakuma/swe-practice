"""Reference solution. CI asserts this passes every test in `tests.py`."""


def find_missing(numbers: list[int]) -> int:
    """Return the one value from 0..len(numbers) that is not in `numbers`.

    XOR is its own inverse (`x ^ x == 0`), has 0 as its identity
    (`x ^ 0 == x`), and is commutative and associative -- so XOR-ing a pile of
    numbers together is a summary that *forgets everything that appears an even
    number of times*, regardless of the order it arrived in.

    Every value in `0..n` therefore appears exactly twice in the fold below
    (once as an index, once as a value) except the missing one, which appears
    only as an index. Everything else cancels and the survivor is the answer.

    `n` is included via `enumerate(..., start=1)`: the indices then run `1..n`
    and the final `result` is seeded with 0, so between them the fold sees
    every number in `0..n` exactly once on the index side.

    The arithmetic version is equally good here:

        return n * (n + 1) // 2 - sum(numbers)

    In Python the two are genuinely interchangeable, because integers do not
    overflow. In a fixed-width language they are not: the sum of 0..n overflows
    a 32-bit int somewhere around n = 92682 while the XOR fold cannot overflow
    at all, since it never produces a value wider than its inputs. That is the
    real reason to know the XOR form.
    """
    result = 0
    for index, value in enumerate(numbers, start=1):
        result ^= index ^ value
    return result
