"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import largest_container


def reference(heights: list[int]) -> int:
    """Largest area by comparing every pair -- an independent oracle."""
    return max(
        [0]
        + [
            min(heights[left], heights[right]) * (right - left)
            for left in range(len(heights))
            for right in range(left + 1, len(heights))
        ]
    )


def test_finds_the_worked_example() -> None:
    """Returns the largest area for the worked example."""
    assert largest_container([1, 8, 6, 2, 5, 4, 8, 3, 7]) == 49


def test_handles_two_lines() -> None:
    """Returns the only area available for two lines."""
    assert largest_container([1, 1]) == 1
    assert largest_container([3, 7]) == 3


def test_handles_fewer_than_two_lines() -> None:
    """Returns 0 when no container can be formed."""
    assert largest_container([]) == 0
    assert largest_container([5]) == 0


def test_handles_equal_heights() -> None:
    """Uses the widest pair when every line is the same height."""
    assert largest_container([4, 4, 4]) == 8
    assert largest_container([2, 2, 2, 2, 2]) == 8


def test_prefers_the_tall_narrow_pair_when_the_product_favours_it() -> None:
    """Chooses two adjacent tall lines over the widest short pair.

    The widest pair is positions 0 and 4, worth min(1, 9) * 4 = 4. The two
    nines are adjacent and worth 9. The decision is the product, so neither
    factor alone predicts the winner.
    """
    assert largest_container([1, 1, 1, 9, 9]) == 9


def test_prefers_the_wide_short_pair_when_the_product_favours_it() -> None:
    """Chooses the widest pair over two taller lines in the middle.

    The mirror of the test above on the same list shape: the sixes at the ends
    are worth 6 * 5 = 30, beating the adjacent nines at 9.
    """
    assert largest_container([6, 1, 9, 9, 1, 6]) == 30


def test_handles_zero_heights() -> None:
    """Treats a zero-height line as holding nothing."""
    assert largest_container([0, 0]) == 0
    assert largest_container([0, 5, 0]) == 0
    assert largest_container([0, 2, 2, 0]) == 2


def test_handles_a_strictly_increasing_series() -> None:
    """Handles heights that only rise."""
    assert largest_container([1, 2, 3, 4, 5]) == 6


def test_handles_a_strictly_decreasing_series() -> None:
    """Handles heights that only fall."""
    assert largest_container([5, 4, 3, 2, 1]) == 6


def test_does_not_stop_at_the_tallest_pair() -> None:
    """Keeps searching past a locally tall pair.

    A solution that walks toward the tallest lines rather than away from the
    shorter one settles for the adjacent hundreds and misses the wide pair of
    nineties that is worth more.
    """
    assert largest_container([90, 1, 100, 100, 1, 1, 1, 90]) == 630


def test_agrees_with_brute_force_on_every_short_series() -> None:
    """Matches an all-pairs search for every list up to length seven.

    Every height list over 0..4, about a hundred thousand cases. The
    which-pointer-to-move rule is a greedy choice, and the usual failure --
    moving the taller line, or moving both -- is wrong only on particular
    shapes.
    """
    for length in range(8):
        for heights in product(range(5), repeat=length):
            values = list(heights)

            assert largest_container(values) == reference(values), values


def test_agrees_with_brute_force_on_a_wider_value_range() -> None:
    """Matches brute force for every length-five list over 0..7."""
    for heights in product(range(8), repeat=5):
        values = list(heights)

        assert largest_container(values) == reference(values), values


def test_leaves_the_input_alone() -> None:
    """Does not sort or mutate the list it was given.

    Sorting destroys the distances, so a solution that sorts is wrong anyway --
    but it must also not quietly reorder the caller's data.
    """
    heights = [1, 8, 6, 2, 5, 4, 8, 3, 7]
    original = list(heights)

    largest_container(heights)

    assert heights == original


def test_scans_a_large_series_in_one_pass() -> None:
    """Handles a million lines within the time limit.

    Comparing every pair is five times ten to the eleventh. The tall lines are
    at both ends so the answer needs the full width, which rules out a solution
    that only inspects a bounded neighbourhood.
    """
    size = 1_000_000
    heights = [1] * size
    heights[0] = 1_000
    heights[-1] = 999

    assert largest_container(heights) == 999 * (size - 1)
