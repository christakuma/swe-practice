"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import ways_to_climb


def test_counts_the_ways_up_three_steps() -> None:
    """Counts 1+1+1, 1+2 and 2+1 as three distinct ways."""
    assert ways_to_climb(3) == 3


def test_counts_the_ways_up_two_steps() -> None:
    """Counts 1+1 and 2 as two ways.

    The smallest case that depends on ways(0) being 1 rather than 0.
    """
    assert ways_to_climb(2) == 2


def test_counts_one_way_up_one_step() -> None:
    """Counts a single way up one step."""
    assert ways_to_climb(1) == 1


def test_counts_one_way_up_no_steps() -> None:
    """Counts taking no steps as one way, not none."""
    assert ways_to_climb(0) == 1


def test_counts_the_ways_up_five_steps() -> None:
    """Counts eight ways up five steps."""
    assert ways_to_climb(5) == 8


def test_treats_the_order_of_steps_as_significant() -> None:
    """Counts 1+2 and 2+1 separately.

    A solution counting *combinations* of step sizes rather than sequences
    returns 2 for four steps (1+1+1+1, 1+1+2, 2+2) instead of 5.
    """
    assert ways_to_climb(4) == 5


def test_handles_a_large_number_of_steps_quickly() -> None:
    """Counts the ways up five hundred steps.

    The naive recursion makes about 2^500 calls. Memoised or iterative, this is
    five hundred additions -- of very large integers, which Python handles and
    most languages do not: the answer has 105 digits, so anything backed by a
    64-bit integer has silently overflowed long before here.
    """
    expected = int(
        "2255915161619363308725126950360720720460113249137581905886388664184"
        "74627738686883405015987052796968498626"
    )

    assert ways_to_climb(500) == expected


def test_grows_the_way_the_recurrence_says() -> None:
    """Satisfies ways(n) = ways(n-1) + ways(n-2) at a sample of sizes."""
    for size in (6, 10, 25, 60):
        assert ways_to_climb(size) == ways_to_climb(size - 1) + ways_to_climb(size - 2)
