"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import max_product


def reference(numbers: list[int]) -> int:
    """Largest product over every contiguous run -- an independent oracle."""
    best = None
    for start in range(len(numbers)):
        running = 1
        for value in numbers[start:]:
            running *= value
            best = running if best is None else max(best, running)
    assert best is not None
    return best


def test_finds_a_positive_run() -> None:
    """Returns the best product from an all-positive prefix."""
    assert max_product([2, 3, -2, 4]) == 6


def test_prefers_a_zero_to_a_negative() -> None:
    """Returns 0 when every non-zero run is negative."""
    assert max_product([-2, 0, -1]) == 0


def test_multiplies_two_negatives_into_the_answer() -> None:
    """Spans a negative to reach a second one.

    The best run is the whole list, and its product is positive only because
    it contains two negatives. A solution tracking just the best product ending
    here discards the -2 as a dead end and answers 3.
    """
    assert max_product([-2, 3, -4]) == 24


def test_handles_a_single_value() -> None:
    """Returns the only value, positive or negative."""
    assert max_product([3]) == 3
    assert max_product([-3]) == -3
    assert max_product([0]) == 0


def test_handles_an_all_negative_list() -> None:
    """Returns a negative answer when every run is negative.

    An odd count of negatives with no zero cannot produce a positive run of
    the whole list. Seeding the running product at 1 instead of at the first
    value wrongly reports 1 here.
    """
    assert max_product([-2]) == -2
    assert max_product([-1, -2, -3]) == 6
    assert max_product([-4, -3, -2]) == 12


def test_handles_an_odd_number_of_negatives() -> None:
    """Drops whichever negative costs least to exclude.

    Five values with three negatives: the best run is [-2, -4, 3], because
    reaching further left to pick up the -5 would need the 2 as well and the
    sign would flip back.
    """
    assert max_product([-1, -2, -3, -4]) == 24
    assert max_product([2, -5, -2, -4, 3]) == 24


def test_restarts_after_a_zero() -> None:
    """Treats a zero as a wall that resets the running product.

    A solution that keeps multiplying through zeros reports 0 for everything
    after the first one.
    """
    assert max_product([-2, 0, 3, 4]) == 12
    assert max_product([1, 0, -1, -2, -3]) == 6


def test_handles_several_zeros() -> None:
    """Handles runs separated by more than one zero."""
    assert max_product([0, 0, 0]) == 0
    assert max_product([2, 0, 0, 5]) == 5
    assert max_product([-1, 0, -1, 0, -1]) == 0


def test_handles_ones_and_minus_ones() -> None:
    """Handles values whose products do not grow."""
    assert max_product([1, 1, 1]) == 1
    assert max_product([-1, -1]) == 1
    assert max_product([-1, -1, -1]) == 1


def test_requires_a_non_empty_run() -> None:
    """Never returns the empty product.

    The run must hold at least one value, so a list of one negative has a
    negative answer. Returning 1 for "take nothing" is the common wrong answer.
    """
    assert max_product([-5]) == -5
    assert max_product([-5, -4]) == 20
    assert max_product([-5, 0]) == 0


def test_agrees_with_brute_force_on_every_short_list() -> None:
    """Matches an all-runs search for every list up to length six.

    Every list over -3..3 up to length six, around a hundred and forty
    thousand cases. Every known failure here -- one running value instead of
    two, the simultaneous-assignment bug, a wrong seed -- depends on a
    particular arrangement of signs and zeros, so enumerating beats choosing.

    Length six rather than seven deliberately: seven is a further factor of
    seven in cases and pushed this file to eight seconds against a ten-second
    limit, which is the kind of margin that fails only on a loaded CI box.
    """
    for length in range(1, 7):
        for values in product(range(-3, 4), repeat=length):
            numbers = list(values)

            assert max_product(numbers) == reference(numbers), numbers


def test_leaves_the_input_alone() -> None:
    """Does not mutate the list it was given."""
    numbers = [2, 3, -2, 4]
    original = list(numbers)

    max_product(numbers)

    assert numbers == original


def test_scans_a_large_list_in_one_pass() -> None:
    """Handles a hundred thousand values within the time limit.

    Every value is 1 except a -2 at the front and a -3 at the back, so the only
    positive run spanning both negatives is the whole list, worth 6. Any run
    containing just one of them is negative and any run containing neither is
    1 -- which means the answer requires carrying the worst-product state
    intact across a hundred thousand steps.
    """
    numbers = [1] * 100_000
    numbers[0] = -2
    numbers[-1] = -3

    assert max_product(numbers) == 6
