"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import cheapest_climb


def by_search(costs: list[int], position: int = -1) -> int:
    """The cheapest climb from `position`, trying both moves every time."""
    if position >= len(costs):
        return 0
    here = costs[position] if position >= 0 else 0
    return here + min(by_search(costs, position + 1), by_search(costs, position + 2))


def test_steps_over_an_expensive_step() -> None:
    """Avoids the costly steps when a route around them exists."""
    assert cheapest_climb([1, 100, 1, 1, 1, 100, 1, 1, 100, 1]) == 6


def test_may_start_on_the_second_step() -> None:
    """Skips the first step when starting on the second is cheaper."""
    assert cheapest_climb([10, 15, 20]) == 15
    assert cheapest_climb([50, 1, 1]) == 1


def test_may_step_over_the_last_step() -> None:
    """Reaches the landing from the step before the last."""
    assert cheapest_climb([1, 2, 50]) == 2
    assert cheapest_climb([3, 4]) == 3


def test_a_single_step_can_be_stepped_over() -> None:
    """Returns 0 for one step, which a move of two passes over."""
    assert cheapest_climb([7]) == 0


def test_no_steps_cost_nothing() -> None:
    """Returns 0 for an empty staircase."""
    assert cheapest_climb([]) == 0


def test_cannot_step_over_two_in_a_row() -> None:
    """Pays for one of two adjacent expensive steps."""
    assert cheapest_climb([1, 90, 80, 1]) == 81
    assert cheapest_climb([5, 5, 5, 5]) == 10


def test_free_steps_cost_nothing() -> None:
    """Handles steps whose cost is zero."""
    assert cheapest_climb([0, 0, 0]) == 0
    assert cheapest_climb([0, 9, 0, 9, 0]) == 0


def test_is_not_greedy_about_the_next_step() -> None:
    """Takes a dearer step now when it avoids a much dearer one later."""
    assert cheapest_climb([1, 2, 100, 1, 100]) == 3
    assert cheapest_climb([0, 1, 2, 2]) == 2


def test_agrees_with_trying_every_climb() -> None:
    """Matches an exhaustive search for every short staircase.

    Every staircase of up to seven steps with costs drawn from 0, 1, 3, 7.
    """
    for size in range(8):
        for chosen in product((0, 1, 3, 7), repeat=size):
            costs = list(chosen)
            assert cheapest_climb(costs) == by_search(costs), costs


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given."""
    costs = [4, 1, 6, 2]

    cheapest_climb(costs)

    assert costs == [4, 1, 6, 2]


def test_climbs_a_hundred_thousand_steps() -> None:
    """Handles a hundred thousand steps without recursing.

    Costs alternate 1 and 1000, so the cheapest climb stands on every cheap
    step and nothing else.
    """
    costs = [1, 1000] * 50_000

    assert cheapest_climb(costs) == 50_000
