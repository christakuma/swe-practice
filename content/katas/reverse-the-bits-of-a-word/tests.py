"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import WORD_BITS, reverse_bits

MAX_WORD = (1 << WORD_BITS) - 1


def reference(value: int) -> int:
    """Reverse a 32-bit word via its binary string -- the banned way.

    Independent of whatever the solution does, which is the point: it is here
    to disagree with a shift-and-mask bug, not to be imitated.
    """
    return int(format(value, f"0{WORD_BITS}b")[::-1], 2)


def test_reverses_zero() -> None:
    """Returns zero for zero."""
    assert reverse_bits(0) == 0


def test_moves_the_lowest_bit_to_the_top() -> None:
    """Sends bit 0 to bit 31.

    This is the case a `while n` loop fails: it stops after one step with the
    result still equal to 1, never shifting through the thirty-one leading
    zeros that the 32-bit width implies.
    """
    assert reverse_bits(1) == 1 << (WORD_BITS - 1)


def test_moves_the_highest_bit_to_the_bottom() -> None:
    """Sends bit 31 to bit 0."""
    assert reverse_bits(1 << (WORD_BITS - 1)) == 1


def test_reverses_an_all_ones_word() -> None:
    """Returns all ones for all ones."""
    assert reverse_bits(MAX_WORD) == MAX_WORD


def test_reverses_every_single_bit_position() -> None:
    """Sends bit k to bit 31 - k for every position in the word."""
    for position in range(WORD_BITS):
        assert reverse_bits(1 << position) == 1 << (WORD_BITS - 1 - position), position


def test_agrees_with_a_string_reversal_on_assorted_values() -> None:
    """Matches an independent string-based reversal.

    The values include small ones, ones with a set high bit, and ones with
    long internal runs of zeros -- the cases where an off-by-one in the shift
    count shows up as a result that is merely half or double the right answer.
    """
    for value in (2, 3, 5, 255, 256, 43_261_596, 123_456_789, MAX_WORD - 1):
        assert reverse_bits(value) == reference(value), value


def test_reverses_the_low_byte_into_the_high_byte() -> None:
    """Moves a run of bits across the whole word rather than within it."""
    assert reverse_bits(0b1111_1111) == 0b1111_1111 << 24


def test_is_its_own_inverse() -> None:
    """Returns the original value when applied twice.

    Reversal is an involution, so this holds for any input -- and it fails
    loudly for a solution that is right about the bits and wrong about the
    width, because the width error does not cancel.
    """
    for value in (0, 1, 7, 43_261_596, 999_999, MAX_WORD):
        assert reverse_bits(reverse_bits(value)) == value, value


def test_stays_inside_the_word() -> None:
    """Returns a value that fits in 32 bits.

    Looping more than thirty-two times, or shifting after the final write,
    produces a number larger than the word -- which Python will happily
    represent rather than truncating for you.
    """
    for value in (1, 255, 43_261_596, MAX_WORD):
        assert 0 <= reverse_bits(value) <= MAX_WORD, value


def test_agrees_with_a_string_reversal_across_a_dense_range() -> None:
    """Matches the string reversal for every value in 0..2047."""
    for value in range(2_048):
        assert reverse_bits(value) == reference(value), value
