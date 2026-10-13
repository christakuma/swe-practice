"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import statistics
from itertools import product

import pytest
from solution import WindowMedian


def medians(size: int, values: list[int]) -> list[float]:
    """The median after each add."""
    stream = WindowMedian(size)
    seen = []
    for value in values:
        stream.add(value)
        seen.append(stream.median())
    return seen


def by_sorting(size: int, values: list[int]) -> list[float]:
    """Sort the last `size` values afresh after every add."""
    return [
        float(statistics.median(values[max(0, end - size) : end]))
        for end in range(1, len(values) + 1)
    ]


def test_follows_the_window_as_it_slides() -> None:
    """Returns the median of the most recent values after each add."""
    assert medians(3, [1, 3, -1, -3, 5, 3, 6, 7]) == [
        1.0,
        2.0,
        1.0,
        -1.0,
        -1.0,
        3.0,
        5.0,
        6.0,
    ]


def test_counts_everything_until_the_window_is_full() -> None:
    """Uses every value so far while fewer than `size` have arrived."""
    assert medians(5, [4, 8, 6]) == [4.0, 6.0, 6.0]
    assert medians(100, [9, 1]) == [9.0, 5.0]


def test_forgets_values_that_have_left() -> None:
    """Stops counting a value once `size` newer ones have arrived."""
    assert medians(2, [100, 1, 2, 3])[-1] == 2.5
    assert medians(1, [4, 10, -3]) == [4.0, 10.0, -3.0]


def test_averages_the_two_middle_values_of_an_even_window() -> None:
    """Returns the mean of the two middle values, which need not be a whole number."""
    assert medians(4, [1, 2, 3, 4, 10])[-2:] == [2.5, 3.5]
    assert medians(2, [1, 2]) == [1.0, 1.5]


def test_always_returns_a_float() -> None:
    """Returns a float even when the median is a whole number."""
    stream = WindowMedian(3)
    stream.add(2)

    assert isinstance(stream.median(), float)
    stream.add(4)
    assert isinstance(stream.median(), float)


def test_one_copy_of_a_repeated_value_leaves_at_a_time() -> None:
    """Keeps the other copies of a value when the oldest copy leaves the window."""
    assert medians(2, [5, 5, 9]) == [5.0, 5.0, 7.0]
    assert medians(3, [7, 7, 7, 1, 1]) == [7.0, 7.0, 7.0, 7.0, 1.0]
    assert medians(3, [2, 9, 2, 9, 2, 9]) == [2.0, 5.5, 2.0, 9.0, 2.0, 9.0]


def test_the_value_that_leaves_is_the_oldest_not_the_smallest() -> None:
    """Evicts by age: a large old value goes while smaller, newer ones stay."""
    assert medians(3, [50, 1, 2, 3]) == [50.0, 25.5, 2.0, 2.0]
    assert medians(3, [1, 50, 60, 70]) == [1.0, 25.5, 50.0, 60.0]


def test_raises_before_anything_is_added() -> None:
    """Raises ValueError for a median of no values, whatever the message says."""
    stream = WindowMedian(3)

    try:
        stream.median()
    except ValueError:
        pass
    else:
        pytest.fail("median() of an empty window did not raise ValueError")


def test_can_be_asked_twice_without_adding() -> None:
    """Returns the same median when asked again with nothing added in between."""
    stream = WindowMedian(2)
    for value in (3, 8, 1):
        stream.add(value)

    assert stream.median() == stream.median() == 4.5


def test_streams_do_not_share_state() -> None:
    """Keeps two streams' windows apart."""
    one, two = WindowMedian(2), WindowMedian(2)
    one.add(1)
    two.add(100)
    one.add(3)

    assert one.median() == 2.0
    assert two.median() == 100.0


def test_agrees_with_sorting_each_window() -> None:
    """Matches a fresh sort of each window for every short stream.

    Every stream of up to six values drawn from 0..3, at every window size
    from 1 to 4.
    """
    for length in range(1, 7):
        for chosen in product(range(4), repeat=length):
            values = list(chosen)
            for size in range(1, 5):
                assert medians(size, values) == by_sorting(size, values), (size, values)


def test_handles_a_long_stream() -> None:
    """Takes 100,000 values through a window of 1,000, asking after each.

    The values are a fixed scramble of 0..99,999, checked against a fresh
    sort at a hundred points along the way.
    """
    count, size = 100_000, 1_000
    values = [(index * 7919) % count for index in range(count)]
    stream = WindowMedian(size)

    for index, value in enumerate(values):
        stream.add(value)
        found = stream.median()
        if index % 1000 == 999:
            window = values[index + 1 - size : index + 1]
            assert found == float(statistics.median(window)), index
