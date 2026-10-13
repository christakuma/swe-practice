"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import KthLargest


def test_reports_the_documented_stream() -> None:
    """Reports the third largest after each value of the worked example."""
    tracker = KthLargest(3)

    assert [tracker.add(value) for value in [4, 5, 8, 2, 3, 5, 10, 9, 4]] == [
        None,
        None,
        4,
        4,
        4,
        5,
        5,
        8,
        8,
    ]


def test_returns_none_until_there_are_k_values() -> None:
    """Returns None while fewer than k values have arrived."""
    tracker = KthLargest(2)

    assert tracker.add(9) is None
    assert tracker.add(1) == 1


def test_is_the_running_maximum_for_k_of_one() -> None:
    """Tracks the largest value when k is 1."""
    tracker = KthLargest(1)

    assert [tracker.add(value) for value in [3, 1, 7, 7]] == [3, 3, 7, 7]


def test_counts_repeats_separately() -> None:
    """Treats equal values as separate entries."""
    tracker = KthLargest(2)

    assert [tracker.add(value) for value in [5, 5, 3]] == [None, 5, 5]


def test_handles_negative_values_and_any_order() -> None:
    """Handles values below zero, rising and falling."""
    falling = KthLargest(2)
    rising = KthLargest(2)

    assert [falling.add(value) for value in [-1, -2, -3]] == [None, -2, -2]
    assert [rising.add(value) for value in [-3, -2, -1]] == [None, -3, -2]


def test_agrees_with_sorting_after_every_addition() -> None:
    """Matches a full sort after each addition, for every short stream and k."""
    for k in range(1, 5):
        for stream in product(range(-1, 3), repeat=6):
            tracker = KthLargest(k)
            seen: list[int] = []
            for value in stream:
                seen.append(value)
                ranked = sorted(seen, reverse=True)
                expected = ranked[k - 1] if len(ranked) >= k else None
                assert tracker.add(value) == expected, (k, stream)


def test_keeps_separate_trackers_apart() -> None:
    """Does not share state between two trackers."""
    first, second = KthLargest(1), KthLargest(1)
    first.add(100)

    assert second.add(1) == 1


def test_handles_two_hundred_thousand_values() -> None:
    """Handles two hundred thousand values within the time limit."""
    tracker = KthLargest(10_000)
    last = None
    for value in range(200_000):
        last = tracker.add((value * 7919) % 200_003)

    assert last is not None
    assert (
        sum(1 for value in range(200_000) if (value * 7919) % 200_003 >= last) == 10_000
    )
