"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import fewest_jumps


def by_table(jumps: list[int]) -> int:
    """The fewest jumps to each position, from every position before it."""
    unreachable = len(jumps) + 1
    fewest = [0] + [unreachable] * (len(jumps) - 1)
    for position in range(1, len(jumps)):
        for earlier in range(position):
            if earlier + jumps[earlier] >= position:
                fewest[position] = min(fewest[position], fewest[earlier] + 1)
    return -1 if fewest[-1] >= unreachable else fewest[-1]


def test_finds_the_fewest_jumps() -> None:
    """Reaches the end of the worked example in two jumps."""
    assert fewest_jumps([2, 3, 1, 1, 4]) == 2


def test_does_not_always_jump_as_far_as_it_can() -> None:
    """Takes a short jump when it sets up a longer one."""
    assert fewest_jumps([2, 5, 1, 1, 1, 1, 1]) == 2
    assert fewest_jumps([3, 1, 4, 1, 1, 1, 1]) == 2


def test_returns_minus_one_when_the_end_is_unreachable() -> None:
    """Returns -1 when a zero blocks every route."""
    assert fewest_jumps([3, 2, 1, 0, 4]) == -1
    assert fewest_jumps([0, 1]) == -1
    assert fewest_jumps([1, 0, 1]) == -1


def test_needs_no_jumps_when_the_start_is_the_end() -> None:
    """Returns 0 for a single position, even one holding a zero."""
    assert fewest_jumps([0]) == 0
    assert fewest_jumps([7]) == 0


def test_takes_one_jump_per_position_when_it_has_to() -> None:
    """Takes a jump per position when every jump is a single step."""
    assert fewest_jumps([1, 1, 1, 1]) == 3


def test_clears_the_list_in_one_jump() -> None:
    """Takes one jump when the first position reaches the end."""
    assert fewest_jumps([5, 0, 0, 0]) == 1
    assert fewest_jumps([1, 0]) == 1


def test_does_not_count_a_zero_that_can_be_jumped_over() -> None:
    """Passes over a zero that an earlier jump clears."""
    assert fewest_jumps([2, 0, 2, 0, 1]) == 2


def test_agrees_with_a_table_for_every_small_list() -> None:
    """Matches a position-by-position table for every list up to length seven."""
    for length in range(1, 8):
        for chosen in product(range(4), repeat=length):
            jumps = list(chosen)
            assert fewest_jumps(jumps) == by_table(jumps), jumps


def test_leaves_the_list_alone() -> None:
    """Does not modify the list it was given."""
    jumps = [2, 3, 1, 1, 4]

    fewest_jumps(jumps)

    assert jumps == [2, 3, 1, 1, 4]


def test_crosses_a_hundred_thousand_positions() -> None:
    """Crosses a hundred thousand positions within the time limit.

    Every jump is at most two, so it takes fifty thousand of them -- and a
    table that looks back at every earlier position does five billion
    comparisons getting there. Then the same list with a wall of two zeros
    half way along, which no jump of two can clear.
    """
    size = 100_001
    jumps = [2] * size

    assert fewest_jumps(jumps) == 50_000

    jumps[50_000] = jumps[50_001] = 0
    jumps[49_999] = 1

    assert fewest_jumps(jumps) == -1
