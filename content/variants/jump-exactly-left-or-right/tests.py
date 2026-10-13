"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import can_reach_a_zero


def by_growing_the_reachable_set(jumps: list[int], start: int) -> bool:
    """Add every landing place of every reachable position until nothing changes."""
    reachable = {start}
    while True:
        landings = {
            position + sign * jumps[position]
            for position in reachable
            for sign in (-1, 1)
            if 0 <= position + sign * jumps[position] < len(jumps)
        }
        if landings <= reachable:
            return any(jumps[position] == 0 for position in reachable)
        reachable |= landings


def test_reaches_a_zero_by_jumping_both_ways() -> None:
    """Finds a route that needs jumps to the left and to the right."""
    assert can_reach_a_zero([4, 2, 3, 0, 3, 1, 2], 5)
    assert can_reach_a_zero([4, 2, 3, 0, 3, 1, 2], 0)


def test_starting_on_a_zero_is_already_there() -> None:
    """Returns True when the starting position holds a 0."""
    assert can_reach_a_zero([0, 5], 0)
    assert can_reach_a_zero([0], 0)
    assert can_reach_a_zero([9, 0, 9], 1)


def test_a_jump_is_exact() -> None:
    """Does not stop short: a jump of two cannot land one step away."""
    assert not can_reach_a_zero([2, 0, 2], 0)
    assert not can_reach_a_zero([3, 0, 0, 5], 0)


def test_a_jump_may_go_left() -> None:
    """Reaches a zero that lies behind the starting position."""
    assert can_reach_a_zero([0, 9, 2], 2)
    assert can_reach_a_zero([0, 1, 1, 1], 3)


def test_a_jump_cannot_leave_the_list() -> None:
    """Refuses jumps past either end, and does not wrap round."""
    assert not can_reach_a_zero([0, 1, 5], 2)
    assert not can_reach_a_zero([4, 0, 9], 0)
    assert not can_reach_a_zero([1, 9, 0], 1)


def test_returns_false_when_no_zero_is_reachable() -> None:
    """Returns False when the reachable positions hold no zero."""
    assert not can_reach_a_zero([3, 0, 2, 1, 2], 2)


def test_returns_false_when_there_is_no_zero_at_all() -> None:
    """Returns False for a list with no zero in it."""
    assert not can_reach_a_zero([1, 1, 1], 0)
    assert not can_reach_a_zero([5], 0)


def test_stops_when_jumps_lead_round_in_a_circle() -> None:
    """Terminates when two positions send you to each other.

    Position 0 jumps to 2 and position 2 jumps back to 0. The zero at
    position 1 is never landed on.
    """
    assert not can_reach_a_zero([2, 0, 2], 2)
    assert not can_reach_a_zero([1, 1, 5, 0], 0)


def test_the_reachable_positions_can_have_gaps() -> None:
    """Does not assume everything up to the furthest landing is reachable.

    From 0 the route goes to 3 and then to 6. Positions 1, 2, 4 and 5 are
    passed over, and the zeros among them do not count.
    """
    assert not can_reach_a_zero([3, 0, 0, 3, 0, 0, 7], 0)
    assert can_reach_a_zero([3, 9, 9, 3, 9, 9, 0], 0)


def test_agrees_with_growing_the_reachable_set() -> None:
    """Matches a fixed-point search for every short list and every start.

    Every list of up to six values drawn from 0..4.
    """
    for size in range(1, 7):
        for chosen in product(range(5), repeat=size):
            jumps = list(chosen)
            for start in range(size):
                expected = by_growing_the_reachable_set(jumps, start)
                assert can_reach_a_zero(jumps, start) == expected, (jumps, start)


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given."""
    jumps = [1, 2, 0, 1]

    can_reach_a_zero(jumps, 0)

    assert jumps == [1, 2, 0, 1]


def test_handles_a_long_walk_without_recursing() -> None:
    """Walks a hundred thousand positions one step at a time.

    Every value is 1 except a 0 at the far end, so the only way there is to
    visit every position on the way. Then the 0 is removed.
    """
    size = 100_000
    jumps = [1] * size
    jumps[-1] = 0

    assert can_reach_a_zero(jumps, 0)
    assert not can_reach_a_zero([1] * size, 0)
