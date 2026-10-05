"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import count_bits


def test_counts_zero_as_no_bits() -> None:
    """Returns zero for an input of zero."""
    assert count_bits(0) == 0


def test_counts_a_single_bit() -> None:
    """Returns one for a power of two."""
    assert count_bits(1) == 1
    assert count_bits(128) == 1


def test_counts_a_mixed_value() -> None:
    """Counts the set bits in a value with gaps."""
    assert count_bits(11) == 3


def test_counts_a_full_byte() -> None:
    """Counts eight bits when every bit in a byte is set."""
    assert count_bits(255) == 8


def test_counts_every_value_in_a_byte() -> None:
    """Agrees with a direct reading of the binary string across 0..255."""
    for value in range(256):
        assert count_bits(value) == bin(value).count("1"), value


def test_counts_alternating_bits() -> None:
    """Counts an alternating pattern rather than a contiguous run."""
    assert count_bits(0b10101010) == 4
    assert count_bits(0b01010101) == 4


def test_counts_bits_above_the_32_bit_boundary() -> None:
    """Counts bits in a value too wide for a 32-bit word.

    A solution written as `for i in range(32)` passes every test above and
    silently truncates here. Python integers have no width, so neither can the
    answer.
    """
    assert count_bits(1 << 40) == 1
    assert count_bits((1 << 40) | 1) == 2


def test_counts_bits_above_the_64_bit_boundary() -> None:
    """Counts bits in a value too wide for a 64-bit word."""
    assert count_bits(1 << 100) == 1
    assert count_bits((1 << 100) - 1) == 100


def test_counts_a_sparse_very_wide_value() -> None:
    """Counts two bits separated by a thousand zeros."""
    assert count_bits((1 << 1_000) | (1 << 3)) == 2


def test_counts_a_dense_very_wide_value() -> None:
    """Counts a value whose every bit is set over a thousand positions."""
    assert count_bits((1 << 1_000) - 1) == 1_000
