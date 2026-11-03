"""The hidden test suite.

Each test's docstring becomes the human-readable label on its `CheckReport`
(PLAN.md §7), so they are written as sentences about what the solution must do
rather than as descriptions of the test.

`solution` is the module the workspace writes your source to; there is no
package to import from, by design -- a kata is one file.
"""

from solution import two_sum


def test_finds_the_pair_in_a_short_list() -> None:
    """Finds the two positions that add up to the target."""
    assert two_sum([2, 7, 11, 15], 9) == (0, 1)


def test_returns_the_smaller_index_first() -> None:
    """Returns the two indices in ascending order."""
    assert two_sum([3, 2, 4], 6) == (1, 2)


def test_handles_a_pair_that_is_not_at_the_start() -> None:
    """Finds a pair that sits at the end of the list."""
    assert two_sum([1, 5, 9, 14, 6], 20) == (3, 4)


def test_does_not_pair_an_element_with_itself() -> None:
    """Uses two distinct positions, even when half the target is in the list.

    `6` is exactly half of `12` and appears once, so a solution that looks up a
    value's complement without excluding the value's own position returns
    `(0, 0)` here and passes every other test in this file.
    """
    assert two_sum([6, 2, 10, 1], 12) == (1, 2)


def test_handles_repeated_values() -> None:
    """Handles a list where the two numbers are equal."""
    assert two_sum([3, 3], 6) == (0, 1)


def test_handles_negative_numbers() -> None:
    """Handles negative values and a negative target."""
    assert two_sum([-3, 4, -7, 1], -10) == (0, 2)


def test_handles_a_target_of_zero() -> None:
    """Handles a target of zero."""
    assert two_sum([5, -5, 2], 0) == (0, 1)


def test_finds_the_pair_in_a_long_list() -> None:
    """Finds the pair in a list far too long to compare every pair.

    A hundred thousand elements, the most the signature allows, with the only
    pair at the very end: about five billion pair checks for the nested loop,
    which is minutes; a dict does it in one pass. The time limit, not this
    assertion, is what fails a quadratic solution -- the complexity claim you
    declare before submitting is never auto-graded (PLAN.md §7).

    It was twenty thousand, and a nested loop finished in 8.1 s against the
    10 s limit and passed. The size is chosen so the slow answer is far over
    the limit rather than near it: timed on a sample and extrapolated, the
    nested loop needs ~200 s, and the quadratics that scan in C (`in` on a
    slice, `list.index`) ~30 s.
    """
    n = 100_000
    numbers = list(range(n))

    # Only the last two positions can reach 2n - 3, so the pair is unique.
    assert two_sum(numbers, 2 * n - 3) == (n - 2, n - 1)


def test_finds_a_pair_separated_by_the_whole_list() -> None:
    """Finds a pair whose two positions are at opposite ends."""
    assert two_sum([8, 1, 2, 3, 12], 20) == (0, 4)
