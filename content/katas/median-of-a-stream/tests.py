"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import statistics
from itertools import product

import pytest
from solution import MedianStream


def test_handles_the_worked_example() -> None:
    """Returns the running median after each addition."""
    stream = MedianStream()

    stream.add(1)
    assert stream.median() == 1.0
    stream.add(3)
    assert stream.median() == 2.0
    stream.add(2)
    assert stream.median() == 2.0


def test_raises_before_anything_is_added() -> None:
    """Raises ValueError when there is no median to report."""
    stream = MedianStream()

    with pytest.raises(ValueError, match="no values"):
        stream.median()


def test_averages_the_two_middle_values() -> None:
    """Averages the middle pair on an even count, as a float.

    A solution returning the lower middle value -- which an off-by-one in the
    size invariant produces -- reports 1 here instead of 1.5.
    """
    stream = MedianStream()
    stream.add(1)
    stream.add(2)

    assert stream.median() == 1.5


def test_returns_a_float() -> None:
    """Returns a float even when the median is a whole number."""
    stream = MedianStream()
    stream.add(2)

    assert stream.median() == 2.0
    assert isinstance(stream.median(), float)

    stream.add(4)
    assert isinstance(stream.median(), float)


def test_handles_a_descending_stream() -> None:
    """Tracks the median when values arrive in decreasing order.

    Descending input puts every new value in the low half, so the rebalancing
    runs on every single insertion -- the opposite stress from ascending input.
    """
    stream = MedianStream()
    expected = [5.0, 4.5, 4.0, 3.5, 3.0]
    for index, value in enumerate([5, 4, 3, 2, 1]):
        stream.add(value)

        assert stream.median() == expected[index], value


def test_handles_an_ascending_stream() -> None:
    """Tracks the median when values arrive in increasing order."""
    stream = MedianStream()
    expected = [1.0, 1.5, 2.0, 2.5, 3.0]
    for index, value in enumerate([1, 2, 3, 4, 5]):
        stream.add(value)

        assert stream.median() == expected[index], value


def test_handles_duplicates() -> None:
    """Counts repeated values separately."""
    stream = MedianStream()
    for _ in range(4):
        stream.add(7)

    assert stream.median() == 7.0

    stream.add(1)
    assert stream.median() == 7.0


def test_handles_negative_values() -> None:
    """Handles values below zero.

    The low half is stored negated, so this is where a sign error shows up.
    """
    stream = MedianStream()
    for value in (-5, -1, -3):
        stream.add(value)

    assert stream.median() == -3.0

    stream.add(-4)
    assert stream.median() == -3.5


def test_handles_values_straddling_zero() -> None:
    """Handles a stream mixing negative and positive values."""
    stream = MedianStream()
    for value in (-10, 10, -20, 20):
        stream.add(value)

    assert stream.median() == 0.0


def test_handles_a_single_value_repeatedly_queried() -> None:
    """Returns the same answer when queried several times without adding.

    `median` must not consume or reorder anything -- a solution that pops from
    its heaps to read them answers correctly once and then wrongly.
    """
    stream = MedianStream()
    stream.add(42)

    assert stream.median() == 42.0
    assert stream.median() == 42.0
    assert stream.median() == 42.0


def test_agrees_with_a_sorting_median_at_every_prefix() -> None:
    """Matches `statistics.median` after every addition, for every short stream.

    Every stream of up to six values over -3..3 -- around a hundred and forty
    thousand prefixes checked. The two invariants fail at specific
    size-and-value combinations, and checking after *every* add rather than at
    the end is what localises them.
    """
    for length in range(1, 7):
        for values in product(range(-3, 4), repeat=length):
            stream = MedianStream()
            seen: list[int] = []
            for value in values:
                stream.add(value)
                seen.append(value)

                assert stream.median() == statistics.median(seen), (values, value)


def test_handles_a_long_stream() -> None:
    """Handles a hundred thousand values, querying throughout.

    A sorted list with bisect insertion is O(n) per add -- five billion element
    moves here -- and re-sorting per query is worse. The values are
    interleaved high and low so the halves rebalance constantly.
    """
    stream = MedianStream()
    seen: list[int] = []
    for index in range(100_000):
        value = index if index % 2 == 0 else -index
        stream.add(value)
        seen.append(value)
        if index % 10_000 == 0:
            assert stream.median() == statistics.median(seen), index

    assert stream.median() == statistics.median(seen)
