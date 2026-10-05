"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.

The orderings here are scrambled deterministically rather than randomly, so a
failed grade reproduces exactly for the person reading it.
"""

from solution import find_missing

STRIDE = 7919  # prime, so stride-indexing is a permutation at any size used here


def scramble(values: list[int]) -> list[int]:
    """Return `values` in a fixed, order-destroying permutation."""
    size = len(values)
    if size == 0:
        return []
    return [values[(index * STRIDE) % size] for index in range(size)]


def without(n: int, missing: int) -> list[int]:
    """Return 0..n with `missing` removed, scrambled."""
    return scramble([value for value in range(n + 1) if value != missing])


def test_finds_a_value_in_the_middle() -> None:
    """Finds a missing value from the middle of the range."""
    assert find_missing([3, 0, 1]) == 2


def test_finds_the_largest_value() -> None:
    """Finds the missing value when it is n itself.

    Nothing in the list hints that the range reaches this high, so a solution
    that only considers values it has seen cannot produce it.
    """
    assert find_missing([0, 1]) == 2
    assert find_missing([0, 1, 2, 3]) == 4


def test_finds_zero() -> None:
    """Finds the missing value when it is zero.

    Zero is the identity for both XOR and addition, so a fold that is seeded
    or bounded wrongly often returns 0 by accident -- and then passes this test
    for the wrong reason. The exhaustive test below is what actually pins it.
    """
    assert find_missing([1]) == 0
    assert find_missing([2, 1, 3]) == 0


def test_handles_an_empty_list() -> None:
    """Returns zero for an empty list, where the whole range is just [0]."""
    assert find_missing([]) == 0


def test_does_not_depend_on_order() -> None:
    """Returns the same answer however the list is arranged."""
    for ordering in ([9, 6, 4, 2, 3, 5, 7, 0, 1], [0, 1, 2, 3, 4, 5, 6, 7, 9]):
        assert find_missing(ordering) == 8


def test_finds_every_missing_value_at_every_small_size() -> None:
    """Agrees for every (size, missing value) pair up to a size of forty.

    This is the test that makes the others redundant and is therefore the one
    worth reading: a bound that is off by one, a fold seeded wrongly, or a
    closed form with the wrong `n` all survive the hand-picked cases above and
    die somewhere in here.
    """
    for n in range(41):
        for missing in range(n + 1):
            assert find_missing(without(n, missing)) == missing, (n, missing)


def test_leaves_the_input_alone() -> None:
    """Does not sort or otherwise mutate the list it was given.

    Sorting in place is a correct way to find the gap and a rude one -- the
    caller still owns that list.
    """
    numbers = [3, 0, 1]
    original = list(numbers)

    find_missing(numbers)

    assert numbers == original


def test_handles_a_large_list() -> None:
    """Finds the gap in a list of a million values."""
    assert find_missing(without(1_000_000, 567_890)) == 567_890


def test_handles_a_large_list_missing_its_largest_value() -> None:
    """Finds the gap when it is at the very top of a large range."""
    size = 200_000
    numbers = list(range(size))

    assert find_missing(numbers) == size


def test_returns_a_plain_integer() -> None:
    """Returns an int rather than a float or a bool."""
    assert type(find_missing([1, 0, 3])) is int
