"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from collections.abc import Iterator

from solution import has_duplicate


class Tripwire(list[int]):
    """A list that refuses to be iterated past `limit` elements.

    The only way to check an *early return* from the outside: a plain list
    cannot tell you how much of it was read. Overriding `__iter__` can, and a
    `list` subclass still satisfies every type and interface expectation.
    """

    def __init__(self, values: list[int], limit: int) -> None:
        super().__init__(values)
        self.limit = limit

    def __iter__(self) -> Iterator[int]:
        for index, value in enumerate(super().__iter__()):
            if index >= self.limit:
                raise AssertionError(
                    f"read element {index} after the answer was already known "
                    f"at element {self.limit - 1}",
                )
            yield value


def test_finds_a_duplicate() -> None:
    """Reports True when a value repeats."""
    assert has_duplicate([1, 2, 3, 1]) is True


def test_reports_a_list_of_distinct_values() -> None:
    """Reports False when every value is distinct."""
    assert has_duplicate([1, 2, 3, 4]) is False


def test_handles_an_empty_list() -> None:
    """Reports False for an empty list."""
    assert has_duplicate([]) is False


def test_handles_a_single_element() -> None:
    """Reports False for a one-element list, which cannot repeat."""
    assert has_duplicate([1]) is False


def test_finds_adjacent_duplicates() -> None:
    """Finds a repeat in neighbouring positions."""
    assert has_duplicate([5, 5]) is True
    assert has_duplicate([1, 2, 2, 3]) is True


def test_finds_duplicates_far_apart() -> None:
    """Finds a repeat whose two positions are at opposite ends."""
    assert has_duplicate([7, 1, 2, 3, 4, 5, 7]) is True


def test_does_not_pair_an_element_with_itself() -> None:
    """Reports False when no value repeats, however the scan is ordered.

    Inserting into the set before checking membership makes every element find
    itself, so this returns True for a list of entirely distinct values.
    """
    assert has_duplicate([1, 2, 3, 4, 5, 6, 7, 8]) is False


def test_handles_negative_values_and_zero() -> None:
    """Compares by value across negatives and zero."""
    assert has_duplicate([-1, 0, 1]) is False
    assert has_duplicate([-1, 0, -1]) is True
    assert has_duplicate([0, 0]) is True


def test_returns_a_bool() -> None:
    """Returns True or False, not a truthy count or None."""
    assert has_duplicate([1, 1]) is True
    assert has_duplicate([1, 2]) is False


def test_returns_as_soon_as_the_answer_is_known() -> None:
    """Stops reading once a repeat has been seen.

    The first two values already settle it, so reading a third is work done
    after the answer was available. This is what rules out
    `len(set(numbers)) != len(numbers)`, which must consume the whole list
    before it can compare the lengths.
    """
    numbers = Tripwire([4, 4, 9, 9, 9], limit=2)

    assert has_duplicate(numbers) is True


def test_returns_early_from_a_long_list() -> None:
    """Answers a million-element list by reading three of them."""
    numbers = Tripwire([1, 2, 1, *range(10, 1_000_000)], limit=3)

    assert has_duplicate(numbers) is True


def test_scans_a_large_distinct_list_without_comparing_every_pair() -> None:
    """Clears a list of 200,000 distinct values within the time limit.

    The worst case, since nothing lets it stop early. Comparing every pair is
    two times ten to the tenth comparisons here; a set makes it one pass.
    """
    assert has_duplicate(list(range(200_000))) is False


def test_finds_a_duplicate_at_the_end_of_a_large_list() -> None:
    """Finds a repeat that only appears in the final position."""
    numbers = [*range(200_000), 0]

    assert has_duplicate(numbers) is True
