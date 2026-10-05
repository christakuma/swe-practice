"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import pairwise, product

from solution import longest_run


def reference(numbers: list[int]) -> int:
    """Longest run by sorting and scanning -- an independent oracle.

    The banned solution, used deliberately: it arranges for runs to be
    adjacent rather than recognising their starts, so it shares no logic with
    the set-based version.
    """
    if not numbers:
        return 0
    values = sorted(set(numbers))
    best = run = 1
    for previous, current in pairwise(values):
        run = run + 1 if current == previous + 1 else 1
        best = max(best, run)
    return best


def test_finds_a_run_scattered_through_the_list() -> None:
    """Finds a run whose members are not adjacent in the list."""
    assert longest_run([100, 4, 200, 1, 3, 2]) == 4


def test_finds_a_longer_run() -> None:
    """Finds the longest of several runs."""
    assert longest_run([0, 3, 7, 2, 5, 8, 4, 6]) == 7


def test_handles_an_empty_list() -> None:
    """Returns 0 for no values."""
    assert longest_run([]) == 0


def test_handles_a_single_value() -> None:
    """Returns 1 for one value."""
    assert longest_run([5]) == 1


def test_collapses_duplicates() -> None:
    """Does not let a repeated value lengthen a run.

    Three copies of 5 are a run of one. A solution counting occurrences rather
    than distinct values reports 3.
    """
    assert longest_run([5, 5, 5]) == 1
    assert longest_run([1, 2, 2, 3]) == 3
    assert longest_run([1, 1, 2, 2, 3, 3]) == 3


def test_handles_values_with_no_run() -> None:
    """Returns 1 when no two values are consecutive."""
    assert longest_run([1, 3, 5, 7]) == 1
    assert longest_run([10, 20, 30]) == 1


def test_handles_negative_values() -> None:
    """Finds a run that spans zero."""
    assert longest_run([-2, -1, 0, 1]) == 4
    assert longest_run([-5, -4, 10]) == 2


def test_prefers_the_longest_not_the_first() -> None:
    """Returns the longest run rather than the earliest one found."""
    assert longest_run([1, 2, 10, 11, 12, 13]) == 4
    assert longest_run([10, 11, 12, 13, 1, 2]) == 4


def test_handles_two_adjacent_runs_separated_by_a_gap() -> None:
    """Does not join two runs across a missing value."""
    assert longest_run([1, 2, 3, 5, 6, 7]) == 3
    assert longest_run([1, 2, 3, 4, 6, 7, 8, 9, 10]) == 5


def test_returns_a_plain_integer() -> None:
    """Returns an int rather than a bool."""
    assert type(longest_run([1, 2])) is int


def test_does_not_mutate_the_input() -> None:
    """Leaves the list alone.

    Sorting in place is a correct way to solve this and destroys the caller's
    ordering.
    """
    numbers = [100, 4, 200, 1, 3, 2]
    before = list(numbers)

    longest_run(numbers)

    assert numbers == before


def test_agrees_with_sort_and_scan_on_every_short_list() -> None:
    """Matches the sorting oracle for every list up to length seven.

    Every list over -2..4, around a million cases at the largest length. The
    duplicate handling and the run-start guard each fail on particular
    multiplicities.
    """
    for length in range(8):
        for values in product(range(-2, 5), repeat=length):
            numbers = list(values)

            assert longest_run(numbers) == reference(numbers), numbers


def test_handles_one_long_run_without_quadratic_work() -> None:
    """Handles a single run of two hundred thousand values.

    The pathological input for this kata. Walking upward from every value --
    rather than only from run-starts -- is twenty billion set lookups here,
    and the set-based solution without the run-start guard is exactly that.
    """
    size = 200_000
    numbers = list(range(size))

    assert longest_run(numbers) == size


def test_handles_a_long_run_given_in_reverse() -> None:
    """Handles a long run presented in descending order.

    Order must not matter, and descending input is where a solution that walks
    *downward* from each value has its own quadratic blow-up.
    """
    size = 200_000
    numbers = list(range(size, 0, -1))

    assert longest_run(numbers) == size


def test_handles_many_short_runs() -> None:
    """Handles a hundred thousand separate runs of two."""
    numbers = [value for base in range(100_000) for value in (base * 3, base * 3 + 1)]

    assert longest_run(numbers) == 2
