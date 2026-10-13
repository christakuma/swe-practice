"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import best_haul


def by_every_choice(houses: list[int]) -> int:
    """Try every set of positions that are pairwise at least three apart."""
    size = len(houses)
    best = 0
    for count in range(size + 1):
        for chosen in combinations(range(size), count):
            apart = all(
                min((b - a) % size, (a - b) % size) >= 3
                for a, b in combinations(chosen, 2)
            )
            if apart:
                best = max(best, sum(houses[index] for index in chosen))
    return best


def test_takes_houses_three_apart() -> None:
    """Takes two houses with two between them on each side."""
    assert best_haul([5, 1, 1, 5, 1, 1]) == 10


def test_takes_only_one_from_a_small_circle() -> None:
    """Takes the single largest when every pair is within two places."""
    assert best_haul([1, 2, 3, 4, 5]) == 5
    assert best_haul([4, 9]) == 9
    assert best_haul([7]) == 7
    assert best_haul([]) == 0


def test_does_not_take_houses_two_apart() -> None:
    """Rejects a pair with only one house between them."""
    assert best_haul([9, 0, 9, 0, 0, 0]) == 9


def test_respects_the_join_of_the_circle() -> None:
    """Does not pair the last house with the first or the second."""
    assert best_haul([9, 0, 0, 0, 0, 9]) == 9
    assert best_haul([0, 9, 0, 0, 0, 9]) == 9


def test_can_use_the_second_and_the_second_to_last() -> None:
    """Takes the two houses either side of the join that are three apart."""
    assert best_haul([0, 9, 0, 0, 9, 0]) == 18


def test_agrees_with_trying_every_choice() -> None:
    """Matches an every-choice search for every circle up to seven houses."""
    for size in range(8):
        for chosen in product(range(3), repeat=size):
            houses = list(chosen)
            assert best_haul(houses) == by_every_choice(houses), houses


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given."""
    houses = [5, 1, 1, 5, 1, 1]

    best_haul(houses)

    assert houses == [5, 1, 1, 5, 1, 1]


def test_handles_a_hundred_thousand_houses() -> None:
    """Handles a hundred thousand houses within the time limit."""
    size = 99_999

    assert best_haul([1] * size) == size // 3
