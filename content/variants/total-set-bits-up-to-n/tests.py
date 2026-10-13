"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import total_bits_up_to


def by_recursion(n: int) -> int:
    """Split at the largest power of two not above n.

    Below that power p = 2**k every column is half ones: k * p / 2. From p
    to n each number has the top bit set, and what is under it is the same
    problem for n - p.
    """
    if n <= 0:
        return 0
    k = n.bit_length() - 1
    power = 1 << k
    return k * (power >> 1) + (n - power + 1) + by_recursion(n - power)


def test_counts_the_small_examples() -> None:
    """Totals the bits for 0 to 5 and for 0 to 7."""
    assert total_bits_up_to(5) == 7
    assert total_bits_up_to(7) == 12


def test_handles_nought_and_one() -> None:
    """Returns 0 for n = 0 and 1 for n = 1."""
    assert total_bits_up_to(0) == 0
    assert total_bits_up_to(1) == 1


def test_agrees_with_counting_every_number() -> None:
    """Matches a number-by-number count for every n up to 3,000."""
    running = 0
    for n in range(3001):
        running += f"{n:b}".count("1")
        assert total_bits_up_to(n) == running, n


def test_is_exact_just_below_a_power_of_two() -> None:
    """Returns k * 2**(k-1) for n = 2**k - 1, at every k up to sixty."""
    for k in range(1, 61):
        assert total_bits_up_to((1 << k) - 1) == k * (1 << (k - 1)), k


def test_handles_a_power_of_two_itself() -> None:
    """Adds exactly one bit when stepping onto a power of two."""
    for k in range(1, 61):
        below = total_bits_up_to((1 << k) - 1)
        assert total_bits_up_to(1 << k) == below + 1, k


def test_handles_enormous_inputs() -> None:
    """Returns exact totals for inputs up to 10**18 within the time limit."""
    for n in (10**18, 10**18 - 1, 999_999_999_999_999_989, 123_456_789_012_345_678):
        assert total_bits_up_to(n) == by_recursion(n), n


def test_returns_an_int() -> None:
    """Returns an int rather than a list or a float."""
    assert type(total_bits_up_to(10)) is int
