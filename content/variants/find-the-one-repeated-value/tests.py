"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

import tracemalloc
from collections import Counter
from itertools import product

from solution import find_duplicate


def test_finds_a_value_that_appears_twice() -> None:
    """Finds the repeated value when it appears exactly twice."""
    assert find_duplicate([1, 3, 4, 2, 2]) == 2
    assert find_duplicate([3, 1, 3, 4, 2]) == 3


def test_handles_the_shortest_list() -> None:
    """Handles two entries, which can only both be 1."""
    assert find_duplicate([1, 1]) == 1


def test_finds_a_value_that_appears_many_times() -> None:
    """Finds a value that appears three or more times.

    Each extra copy pushes another value out of the list, so the total says
    nothing useful about which value repeats.
    """
    assert find_duplicate([2, 2, 2, 2, 2]) == 2
    assert find_duplicate([1, 4, 4, 2, 4]) == 4
    assert find_duplicate([3, 3, 3, 1]) == 3


def test_finds_the_largest_and_smallest_values() -> None:
    """Finds the repeat when it is 1 and when it is n."""
    assert find_duplicate([1, 2, 3, 4, 1]) == 1
    assert find_duplicate([4, 1, 2, 3, 4]) == 4
    assert find_duplicate([1, 1, 2]) == 1


def test_finds_copies_wherever_they_sit() -> None:
    """Finds the repeat when its copies are adjacent, far apart, first and last."""
    assert find_duplicate([5, 5, 1, 2, 3, 4]) == 5
    assert find_duplicate([5, 1, 2, 3, 4, 5]) == 5
    assert find_duplicate([1, 2, 3, 4, 5, 5]) == 5


def test_agrees_with_counting_on_every_short_list() -> None:
    """Matches a count of every value for every valid short list.

    Every list of n + 1 values from 1..n, for n up to 5, in which exactly one
    value appears more than once.
    """
    checked = 0
    for top in range(1, 6):
        for chosen in product(range(1, top + 1), repeat=top + 1):
            repeated = [value for value, count in Counter(chosen).items() if count > 1]
            if len(repeated) == 1:
                assert find_duplicate(list(chosen)) == repeated[0], chosen
                checked += 1
    assert checked > 5000


def test_leaves_the_list_as_it_found_it() -> None:
    """Does not reorder, negate or overwrite any entry."""
    numbers = [3, 1, 3, 4, 2, 6, 5]
    before = list(numbers)

    find_duplicate(numbers)

    assert numbers == before


def test_uses_constant_extra_space() -> None:
    """Allocates no memory that grows with the list.

    Two hundred thousand entries: 1, 2, 3 and so on in order, with one more
    copy of 150,000 on the end. A set of the values seen holds 150,000 of them
    before it meets the repeat, and a sorted copy holds them all. The list is
    built before measuring starts.
    """
    top = 200_000
    numbers = [*range(1, top + 1), 150_000]

    tracemalloc.start()
    found = find_duplicate(numbers)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert found == 150_000
    assert peak < 64_000, f"allocated {peak} bytes"


def test_searches_a_million_entries() -> None:
    """Finds the repeat among a million entries within the time limit."""
    top = 1_000_000
    numbers = [*range(2, top + 1), 7, 1]

    assert find_duplicate(numbers) == 7
