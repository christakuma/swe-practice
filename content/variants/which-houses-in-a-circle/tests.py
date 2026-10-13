"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.

Several selections can tie, so nothing here compares against one expected
list except where the best selection is unique. `check` asks the three
questions that make a selection right: is it a list of positions in order,
are no two of them neighbours in the circle, and does it add up to the best
total.
"""

from itertools import pairwise, product

from solution import best_haul


def best_total(houses: list[int]) -> int:
    """The largest total, by trying every subset. An oracle for short circles."""
    count = len(houses)
    best = 0
    for mask in range(1 << count):
        chosen = [i for i in range(count) if mask >> i & 1]
        if allowed(chosen, count):
            best = max(best, sum(houses[i] for i in chosen))
    return best


def allowed(chosen: list[int], count: int) -> bool:
    """Whether no two chosen positions are neighbours in a circle of `count`."""
    if any(second - first == 1 for first, second in pairwise(chosen)):
        return False
    return not (count > 1 and chosen and chosen[0] == 0 and chosen[-1] == count - 1)


def check(houses: list[int], total: int) -> None:
    before = list(houses)
    picks = best_haul(houses)

    assert houses == before, "the list of houses was changed"
    assert isinstance(picks, list), f"expected a list of positions, got {picks!r}"
    assert all(isinstance(i, int) and 0 <= i < len(houses) for i in picks), picks
    assert all(first < second for first, second in pairwise(picks)), (
        f"not ascending: {picks}"
    )
    assert allowed(picks, len(houses)), f"{picks} takes two neighbours"
    assert sum(houses[i] for i in picks) == total, (picks, total)


def test_returns_positions_rather_than_a_total() -> None:
    """Returns the position of the one house worth taking."""
    assert best_haul([2, 3, 2]) == [1]


def test_takes_alternate_houses() -> None:
    """Returns both houses of the best pair, in ascending order."""
    assert best_haul([1, 2, 3, 1]) == [0, 2]


def test_handles_no_houses_and_one_house() -> None:
    """Returns nothing for no houses and position 0 for a single house."""
    assert best_haul([]) == []
    assert best_haul([5]) == [0]


def test_two_houses_are_neighbours() -> None:
    """Takes only the richer of two houses."""
    assert best_haul([3, 8]) == [1]
    assert best_haul([8, 3]) == [0]


def test_does_not_take_the_first_and_the_last() -> None:
    """Treats the first and last house as neighbours.

    In a straight line the two 9s would both be taken. Here they cannot be,
    and the best is one 9 with the 2 that is not beside it.
    """
    assert best_haul([9, 1, 2, 9]) == [0, 2]
    assert best_haul([9, 2, 1, 1, 9]) == [1, 4]


def test_the_best_selection_may_use_the_last_house() -> None:
    """Returns positions in the circle when the answer includes the last house.

    Only the line that omits the first house can find these, and that line
    numbers its own houses from zero. Forgetting to shift its picks back
    gives positions one too low.
    """
    assert best_haul([1, 1, 9, 1, 9]) == [2, 4]
    assert best_haul([1, 0, 7, 1, 1, 7]) == [2, 5]


def test_the_best_selection_may_leave_out_the_last_house() -> None:
    """Returns the selection that uses house 0 when that one is better."""
    assert best_haul([9, 1, 9, 1, 1]) == [0, 2]


def test_may_skip_two_houses_in_a_row() -> None:
    """Leaves a gap of two where alternating would cost more than it gains."""
    assert best_haul([5, 1, 1, 5, 1, 1]) == [0, 3]
    assert best_haul([1, 8, 2, 1, 9, 1]) == [1, 4]


def test_accepts_any_selection_when_several_tie() -> None:
    """Returns a valid best selection when more than one exists."""
    check([4, 4, 4, 4], 8)
    check([1, 1, 1], 1)
    check([2, 1, 2, 1, 2], 4)


def test_handles_houses_holding_nothing() -> None:
    """Returns a valid selection when some or all houses are empty."""
    check([0, 0, 0], 0)
    check([0], 0)
    check([0, 5, 0], 5)


def test_agrees_with_trying_every_subset_on_every_short_circle() -> None:
    """Returns a valid selection with the best total for every short circle.

    Up to six houses with amounts drawn from 0, 1, 2 and 5, so ties and empty
    houses are both common, and up to nine with amounts of 1 and 3.
    """
    for count in range(7):
        for houses in product((0, 1, 2, 5), repeat=count):
            check(list(houses), best_total(list(houses)))
    for count in range(7, 10):
        for houses in product((1, 3), repeat=count):
            check(list(houses), best_total(list(houses)))


def test_handles_a_hundred_thousand_houses() -> None:
    """Chooses from a hundred thousand houses.

    Rich and poor alternate, so the best selection is unique: every rich
    house, and the circle has an even number so none of them are neighbours.
    """
    size = 100_000
    houses = [7 if position % 2 == 0 else 1 for position in range(size)]

    assert best_haul(houses) == list(range(0, size, 2))


def test_handles_an_odd_circle_of_equal_houses() -> None:
    """Takes half of an odd circle, rounded down.

    With 99,999 equal houses, alternating all the way round would put the
    first and last side by side.
    """
    size = 99_999

    check([3] * size, 3 * (size // 2))
