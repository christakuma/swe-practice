"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import WORD_BITS, rotate_left

MAX_WORD = (1 << WORD_BITS) - 1

ASSORTED = (
    0,
    1,
    2,
    3,
    0xFF,
    0x100,
    0x12345678,
    0x80000000,
    0x80000001,
    0xDEADBEEF,
    MAX_WORD - 1,
)


def by_moving_characters(value: int, places: int) -> int:
    """Rotate a 32-bit word via its binary string -- the banned way.

    Takes one character off the front and puts it on the back, `places`
    times. Independent of shifts and of any arithmetic on `places`.
    """
    digits = format(value, f"0{WORD_BITS}b")
    for _ in range(places):
        digits = digits[1:] + digits[0]
    return int(digits, 2)


def test_a_small_rotation_of_a_small_value_is_a_shift() -> None:
    """Shifts the bits up when none of them reaches the top of the word."""
    assert rotate_left(0b1011, 2) == 0b101100
    assert rotate_left(1, 4) == 16


def test_rotating_by_zero_changes_nothing() -> None:
    """Returns the word unchanged for k = 0."""
    assert rotate_left(0x12345678, 0) == 0x12345678
    assert rotate_left(MAX_WORD, 0) == MAX_WORD
    assert rotate_left(0, 0) == 0


def test_the_top_bit_wraps_round_to_the_bottom() -> None:
    """Sends bit 31 to bit 0 when rotating by one."""
    assert rotate_left(0x80000000, 1) == 1
    assert rotate_left(0x80000001, 1) == 3


def test_the_result_stays_inside_the_word() -> None:
    """Never returns a value with a bit set above position 31.

    A left shift in Python keeps the bits it pushes past the top. Without a
    mask, they are still in the answer.
    """
    assert rotate_left(0xF0000000, 4) == 0x0000000F
    for value in ASSORTED:
        for places in range(WORD_BITS + 1):
            assert 0 <= rotate_left(value, places) <= MAX_WORD, (value, places)


def test_rotates_whole_bytes() -> None:
    """Moves the leading hexadecimal digits to the end, in order."""
    assert rotate_left(0x12345678, 8) == 0x34567812
    assert rotate_left(0x12345678, 16) == 0x56781234
    assert rotate_left(0x12345678, 4) == 0x23456781


def test_rotates_left_and_not_right() -> None:
    """Moves bits towards the top of the word."""
    assert rotate_left(1, 1) == 2
    assert rotate_left(0x12345678, 24) == 0x78123456


def test_a_full_turn_changes_nothing() -> None:
    """Returns the word unchanged after rotating by exactly the width."""
    assert rotate_left(0x12345678, 32) == 0x12345678
    assert rotate_left(1, 32) == 1
    assert rotate_left(0xDEADBEEF, 64) == 0xDEADBEEF


def test_k_may_exceed_the_width() -> None:
    """Rotates by the remainder when k is larger than 32."""
    assert rotate_left(0x12345678, 40) == 0x34567812
    assert rotate_left(1, 33) == 2
    assert rotate_left(0x80000000, 65) == 1


def test_handles_an_enormous_k() -> None:
    """Rotates by a thousand million places without doing it one at a time.

    A thousand million is a multiple of 32 -- it is 2**9 times 5**9 -- so
    that rotation changes nothing, and seven more is a rotation by seven.
    """
    assert rotate_left(0x12345678, 10**9) == 0x12345678
    assert rotate_left(1, 10**9 + 7) == 128
    assert rotate_left(0x80000001, 10**9 + 1) == 3


def test_zero_and_all_ones_are_unchanged_by_any_rotation() -> None:
    """Returns the same word when every bit is the same."""
    for places in (0, 1, 13, 31, 32, 45):
        assert rotate_left(0, places) == 0
        assert rotate_left(MAX_WORD, places) == MAX_WORD


def test_moves_every_single_bit_to_every_position() -> None:
    """Sends bit b to bit (b + k) mod 32, for every b and every k up to two turns."""
    for position in range(WORD_BITS):
        for places in range(2 * WORD_BITS + 1):
            expected = 1 << ((position + places) % WORD_BITS)

            assert rotate_left(1 << position, places) == expected, (position, places)


def test_agrees_with_moving_characters_on_assorted_values() -> None:
    """Matches a string rotation done one character at a time.

    Every value in a mixed bag, by every amount up to seventy.
    """
    for value in ASSORTED:
        for places in range(71):
            assert rotate_left(value, places) == by_moving_characters(value, places), (
                value,
                places,
            )


def test_two_rotations_add_up() -> None:
    """Rotating by a and then by b is the same as rotating by a + b."""
    for value in ASSORTED:
        for first, second in ((1, 1), (5, 27), (31, 31), (16, 17), (0, 9)):
            twice = rotate_left(rotate_left(value, first), second)

            assert twice == rotate_left(value, first + second), (value, first, second)
