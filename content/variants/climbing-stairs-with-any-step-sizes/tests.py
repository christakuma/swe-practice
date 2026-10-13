"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations

from solution import ways_to_climb


def by_listing(steps: int, sizes: tuple[int, ...]) -> int:
    """Count the sequences by actually walking every one of them."""
    if steps == 0:
        return 1
    return sum(by_listing(steps - size, sizes) for size in sizes if size <= steps)


def test_counts_with_three_step_sizes() -> None:
    """Counts seven ways up four steps with sizes of one, two and three."""
    assert ways_to_climb(4, [1, 2, 3]) == 7


def test_matches_the_standard_problem_for_ones_and_twos() -> None:
    """Gives the standard answers when the sizes are one and two."""
    assert [ways_to_climb(steps, [1, 2]) for steps in range(7)] == [
        1,
        1,
        2,
        3,
        5,
        8,
        13,
    ]


def test_returns_zero_when_the_top_cannot_be_reached() -> None:
    """Returns 0 when no sequence of moves lands exactly on the top."""
    assert ways_to_climb(5, [2]) == 0
    assert ways_to_climb(1, [2, 3]) == 0


def test_counts_one_way_to_climb_nothing() -> None:
    """Counts one way to climb zero steps, whatever the sizes."""
    assert ways_to_climb(0, [1, 2]) == 1
    assert ways_to_climb(0, [7]) == 1


def test_counts_orderings_separately() -> None:
    """Counts 1+5 and 5+1 as two different ways."""
    assert ways_to_climb(6, [1, 5]) == 3


def test_does_not_depend_on_the_order_of_the_sizes() -> None:
    """Gives the same answer however the sizes are listed."""
    assert ways_to_climb(6, [5, 1]) == 3
    assert ways_to_climb(10, [3, 1, 2]) == ways_to_climb(10, [1, 2, 3])


def test_handles_a_single_size() -> None:
    """Counts exactly one way when one size divides the height."""
    assert ways_to_climb(12, [4]) == 1
    assert ways_to_climb(7, [1]) == 1


def test_agrees_with_listing_every_sequence() -> None:
    """Matches a count made by walking every sequence, for every small case.

    Every non-empty set of sizes drawn from 1..5, at every height up to
    twelve.
    """
    for count in range(1, 4):
        for sizes in combinations(range(1, 6), count):
            for steps in range(13):
                expected = by_listing(steps, sizes)
                assert ways_to_climb(steps, list(sizes)) == expected, (steps, sizes)


def test_leaves_the_sizes_alone() -> None:
    """Does not sort or modify the list of sizes."""
    sizes = [3, 1, 2]

    ways_to_climb(5, sizes)

    assert sizes == [3, 1, 2]


def test_counts_a_tall_staircase_exactly() -> None:
    """Returns an exact count for five hundred steps.

    Checked against a rolling three-term sum, which is what sizes of one, two
    and three reduce to. The answer has over a hundred and thirty digits, so a
    float anywhere in the arithmetic fails this.
    """
    before, last, current = 0, 0, 1
    for _ in range(500):
        before, last, current = last, current, before + last + current

    assert ways_to_climb(500, [1, 2, 3]) == current
