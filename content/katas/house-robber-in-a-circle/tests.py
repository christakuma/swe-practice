"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import best_haul


def reference(houses: list[int]) -> int:
    """Best total by enumerating every subset -- an independent oracle.

    Bitmask over the houses: reject any subset with two adjacent bits, and
    reject the wrap-around pair separately. It shares no recurrence with the
    intended solution. Exponential, and fine at these sizes.
    """
    size = len(houses)
    if size == 0:
        return 0
    if size == 1:
        return houses[0]
    best = 0
    for mask in range(1 << size):
        if mask & (mask >> 1):
            continue  # two adjacent in the straight line
        if mask & 1 and mask >> (size - 1) & 1:
            continue  # first and last, which are adjacent in a circle
        best = max(best, sum(houses[i] for i in range(size) if mask >> i & 1))
    return best


def test_refuses_to_wrap_around() -> None:
    """Does not take both the first and last houses.

    The two 2s total 4 and are neighbours in a circle, so the answer is the
    middle 3. A solution that ignores the circle -- the straight-line answer --
    reports 4.
    """
    assert best_haul([2, 3, 2]) == 3


def test_handles_the_worked_example() -> None:
    """Returns the best non-adjacent total."""
    assert best_haul([1, 2, 3, 1]) == 4


def test_handles_an_empty_list() -> None:
    """Returns 0 for no houses."""
    assert best_haul([]) == 0


def test_handles_a_single_house() -> None:
    """Returns the one amount.

    The only input where both "omit the first" and "omit the last" slices are
    empty, so a solution that splits without guarding this reports 0.
    """
    assert best_haul([5]) == 5
    assert best_haul([0]) == 0


def test_handles_two_houses() -> None:
    """Takes the larger of two, which are adjacent both ways."""
    assert best_haul([1, 2]) == 2
    assert best_haul([2, 1]) == 2
    assert best_haul([3, 3]) == 3


def test_handles_three_houses() -> None:
    """Takes the single best of three, all mutually adjacent in a circle."""
    assert best_haul([1, 2, 3]) == 3
    assert best_haul([5, 1, 1]) == 5


def test_takes_alternate_houses_when_that_is_best() -> None:
    """Takes every other house around an even-length circle."""
    assert best_haul([1, 1, 1, 1]) == 2
    assert best_haul([2, 1, 2, 1]) == 4
    assert best_haul([1, 3, 1, 3, 1, 3]) == 9


def test_handles_an_odd_length_circle() -> None:
    """Handles an odd circle, where no perfect alternation exists."""
    assert best_haul([1, 1, 1, 1, 1]) == 2
    assert best_haul([4, 1, 4, 1, 4]) == 8


def test_handles_zeros() -> None:
    """Treats a zero house as takeable but worthless.

    The last case is the sharpest wrap-around in this file: two 5s with two
    zeros between them, and they *still* cannot both be taken, because in a
    circle of four, positions 0 and 3 are neighbours. The intervening zeros
    make it look safe and it is not.
    """
    assert best_haul([0, 0, 0]) == 0
    assert best_haul([0, 5, 0]) == 5
    assert best_haul([5, 0, 0, 5]) == 5


def test_allows_the_first_and_last_when_not_both() -> None:
    """Takes the first or the last, just not both."""
    assert best_haul([9, 1, 1, 1]) == 10
    assert best_haul([1, 1, 1, 9]) == 10


def test_returns_a_plain_integer() -> None:
    """Returns an int rather than a bool."""
    assert type(best_haul([1, 2])) is int


def test_does_not_mutate_the_input() -> None:
    """Leaves the list alone."""
    houses = [2, 3, 2]
    before = list(houses)

    best_haul(houses)

    assert houses == before


def test_agrees_with_a_subset_search_on_every_small_circle() -> None:
    """Matches an exhaustive subset search for every circle up to eight houses.

    Nearly ten thousand circles over three amounts. The wrap-around rule and
    the single-house guard each fail only at particular lengths, and parity
    matters -- odd circles have no clean alternation -- so sweeping the length
    is what settles it.
    """
    for size in range(9):
        for amounts in product([0, 1, 4], repeat=size):
            houses = list(amounts)

            assert best_haul(houses) == reference(houses), houses


def test_handles_a_large_circle() -> None:
    """Handles a hundred thousand houses within the time limit.

    Alternating 1 and 2 over an even length, so the answer is every 2 -- which
    requires taking half the houses and never wrapping.
    """
    houses = [1, 2] * 50_000

    assert best_haul(houses) == 100_000
