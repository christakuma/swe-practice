"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import longest_positive_slice


def by_multiplying_every_slice(numbers: list[int]) -> int:
    """The answer by computing every slice's product. An oracle for short lists."""
    best = 0
    for start in range(len(numbers)):
        running = 1
        for end in range(start, len(numbers)):
            running *= numbers[end]
            if running > 0:
                best = max(best, end - start + 1)
    return best


def test_two_negatives_cancel() -> None:
    """Returns the whole length when the negatives come in a pair."""
    assert longest_positive_slice([1, -2, -3, 4]) == 4


def test_all_positive_values_give_the_whole_list() -> None:
    """Returns the full length when nothing is negative or zero."""
    assert longest_positive_slice([3, 1, 4, 1, 5]) == 5


def test_a_single_value() -> None:
    """Returns 1 for a positive value and 0 for a negative one or a zero."""
    assert longest_positive_slice([7]) == 1
    assert longest_positive_slice([-5]) == 0
    assert longest_positive_slice([0]) == 0


def test_one_negative_must_be_left_out() -> None:
    """Returns the longer side of a lone negative."""
    assert longest_positive_slice([1, 2, -3, 4]) == 2
    assert longest_positive_slice([1, -3, 4, 5, 6]) == 3
    assert longest_positive_slice([-1, 2]) == 1


def test_with_three_negatives_drops_the_first_or_the_last() -> None:
    """Leaves out whichever end negative costs fewer values.

    The slice after the first negative and the slice before the last one
    both have two negatives. The longer wins.
    """
    assert longest_positive_slice([1, -1, 2, 3, -1, 4, -1, 5, 6, 7]) == 8
    assert longest_positive_slice([1, 2, 3, -1, 4, -1, 5, -1, 6]) == 7
    assert longest_positive_slice([0, 1, -2, -3, -4]) == 3


def test_a_zero_splits_the_list() -> None:
    """Does not let a slice run across a zero."""
    assert longest_positive_slice([1, 2, 0, 3, 4, 5]) == 3
    assert longest_positive_slice([-1, -2, 0, -3, -4, 5]) == 3
    assert longest_positive_slice([0, 0, 0]) == 0


def test_a_zero_forgets_the_negatives_before_it() -> None:
    """Counts negatives afresh after a zero.

    One negative before the zero and one after do not make a pair.
    """
    assert longest_positive_slice([-1, 0, -1, 2, 3]) == 2
    assert longest_positive_slice([2, -1, 0, 3, -1]) == 1


def test_a_positive_value_alone_does_not_make_a_negative_slice() -> None:
    """Does not invent a negative-product slice out of positive values.

    After 1, 2 there is no slice with a negative product. A solution that
    says there is one will pair it with the -3 and report three.
    """
    assert longest_positive_slice([1, 2, -3]) == 2
    assert longest_positive_slice([5, -1]) == 1


def test_only_negatives() -> None:
    """Returns the largest even number of values from a run of negatives."""
    assert longest_positive_slice([-1, -1, -1, -1]) == 4
    assert longest_positive_slice([-1, -1, -1]) == 2
    assert longest_positive_slice([-2]) == 0


def test_agrees_with_multiplying_every_slice() -> None:
    """Matches a computed product for every list of up to eight values.

    Values are drawn from -2, 0 and 3, which is every combination of signs
    there is.
    """
    for size in range(1, 9):
        for values in product((-2, 0, 3), repeat=size):
            numbers = list(values)
            expected = by_multiplying_every_slice(numbers)

            assert longest_positive_slice(numbers) == expected, numbers


def test_handles_a_hundred_thousand_large_values() -> None:
    """Scans a hundred thousand values near a thousand million.

    Every thousandth value is negative, a hundred of them in all, so the
    whole list has a positive product and it is one no-one should compute.
    Turning the value at position 250 negative makes a hundred and one, and
    the best slice is everything after it: leaving out the last negative
    instead would cost the final five hundred values.
    """
    size = 100_000
    numbers = [
        -999_999_937 if position % 1_000 == 500 else 999_999_937
        for position in range(size)
    ]

    assert longest_positive_slice(numbers) == size

    numbers[250] = -999_999_937

    assert longest_positive_slice(numbers) == size - 251
