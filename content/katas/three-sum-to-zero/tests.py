"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import combinations, product

from solution import three_sum


def reference(numbers: list[int]) -> list[tuple[int, int, int]]:
    """Every zero-summing triple, by brute force over index combinations.

    An independent oracle: it works from positions rather than from sorted
    order, so it shares no deduplication logic with a two-pointer solution.
    """
    found = {
        tuple(sorted(triple)) for triple in combinations(numbers, 3) if sum(triple) == 0
    }
    return sorted(found)


def test_finds_the_worked_example() -> None:
    """Returns both triples from the worked example, deduplicated."""
    assert three_sum([-1, 0, 1, 2, -1, -4]) == [(-1, -1, 2), (-1, 0, 1)]


def test_handles_all_zeros() -> None:
    """Returns the all-zero triple exactly once from four zeros.

    Four zeros give four index combinations and one distinct triple. A
    solution that does not skip repeated pointer values returns it twice.
    """
    assert three_sum([0, 0, 0, 0]) == [(0, 0, 0)]


def test_returns_nothing_when_no_triple_sums_to_zero() -> None:
    """Returns an empty list when there is no answer."""
    assert three_sum([1, 2, 3]) == []
    assert three_sum([-1, -2, -3]) == []


def test_handles_lists_too_short_for_a_triple() -> None:
    """Returns an empty list for fewer than three values."""
    assert three_sum([]) == []
    assert three_sum([0]) == []
    assert three_sum([0, 0]) == []


def test_requires_three_distinct_positions() -> None:
    """Does not reuse one position to fill two slots.

    A single 0 cannot make (0, 0, 0), and a single -2 with one 1 cannot make
    (-2, 1, 1). A solution that searches by value rather than by position
    returns a triple here.
    """
    assert three_sum([0, 1, 2]) == []
    assert three_sum([-2, 1, 5]) == []


def test_uses_a_repeated_value_when_there_are_enough_copies() -> None:
    """Allows a value twice when the list holds it twice.

    The mirror of the test above: two -1s genuinely do make (-1, -1, 2), so a
    deduplication rule that forbids repeated *values* rather than repeated
    *triples* drops a real answer.
    """
    assert three_sum([-1, -1, 2]) == [(-1, -1, 2)]


def test_deduplicates_identical_triples_from_different_positions() -> None:
    """Returns one entry when many index combinations give the same triple."""
    assert three_sum([-1, -1, -1, 2, 2, 2]) == [(-1, -1, 2)]


def test_returns_triples_sorted_within_and_between() -> None:
    """Returns ascending tuples in ascending order."""
    result = three_sum([-4, -2, -2, 0, 1, 2, 3, 4, 6])

    assert result == sorted(result)
    for triple in result:
        assert list(triple) == sorted(triple)
        assert sum(triple) == 0


def test_finds_several_distinct_triples() -> None:
    """Returns every distinct triple when there is more than one."""
    assert three_sum([-4, -1, -1, 0, 1, 2]) == [(-1, -1, 2), (-1, 0, 1)]


def test_handles_only_positive_and_only_negative_lists() -> None:
    """Returns nothing when every value shares a sign."""
    assert three_sum([1, 2, 3, 4, 5]) == []
    assert three_sum([-1, -2, -3, -4]) == []


def test_agrees_with_brute_force_on_every_short_list() -> None:
    """Matches an all-combinations search for every list up to length five.

    Every list over -3..3, around twenty thousand cases. All three
    deduplication skips -- the fixed value, and the two pointers after a hit --
    fail only on particular multiplicities, so enumerating beats choosing.
    """
    for length in range(6):
        for values in product(range(-3, 4), repeat=length):
            numbers = list(values)

            assert three_sum(numbers) == reference(numbers), numbers


def test_agrees_with_brute_force_on_longer_lists_with_many_duplicates() -> None:
    """Matches brute force for every length-six list over -2..2.

    A narrower value range at a longer length, so triples collide constantly
    and the deduplication is under real pressure.
    """
    for values in product(range(-2, 3), repeat=6):
        numbers = list(values)

        assert three_sum(numbers) == reference(numbers), numbers


def test_leaves_the_input_alone() -> None:
    """Does not sort the caller's list in place.

    Sorting is the right first move and `numbers.sort()` is the wrong way to
    do it -- the caller still owns that list.
    """
    numbers = [-1, 0, 1, 2, -1, -4]
    original = list(numbers)

    three_sum(numbers)

    assert numbers == original


def test_handles_a_large_list_without_cubic_work() -> None:
    """Searches two thousand values within the time limit.

    Three nested loops is eight times ten to the ninth here. The values are
    spread so that few triples hit zero, which keeps the output small and
    makes this a test of the search rather than of the collection.
    """
    numbers = [value * 2 for value in range(-1_000, 1_000)]

    result = three_sum(numbers)

    assert all(sum(triple) == 0 for triple in result)
    assert result == sorted(set(result))
    assert (-1_998, 0, 1_998) in result
