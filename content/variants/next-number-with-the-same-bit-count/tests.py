"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import next_with_same_bits


def ones(n: int) -> int:
    return bin(n).count("1")


def by_counting_up(n: int) -> int:
    """The first number above n with the same count, found by trying each."""
    candidate = n + 1
    while ones(candidate) != ones(n):
        candidate += 1
    return candidate


def test_swaps_the_lowest_zero_one_pair() -> None:
    """Moves a lone low 1 up past the 0 above it."""
    assert next_with_same_bits(0b1011) == 0b1101
    assert next_with_same_bits(0b0101) == 0b0110
    assert next_with_same_bits(0b1001) == 0b1010


def test_a_single_bit_moves_up_one_place() -> None:
    """Doubles a power of two."""
    assert next_with_same_bits(1) == 2
    assert next_with_same_bits(2) == 4
    assert next_with_same_bits(64) == 128


def test_the_rest_of_a_block_falls_to_the_bottom() -> None:
    """Moves the top of a block up and packs the rest at bit zero."""
    assert next_with_same_bits(0b0110) == 0b1001
    assert next_with_same_bits(0b111000) == 0b1000011
    assert next_with_same_bits(0b10110) == 0b11001


def test_a_number_of_all_ones_grows_by_a_bit() -> None:
    """Handles a number with no 0 above its lowest block to move into."""
    assert next_with_same_bits(0b111) == 0b1011
    assert next_with_same_bits(0b11111) == 0b101111


def test_only_the_lowest_block_moves() -> None:
    """Leaves the higher bits of the number alone."""
    assert next_with_same_bits(0b110_0110) == 0b110_1001
    assert next_with_same_bits(0b1010_1100) == 0b1011_0001


def test_keeps_the_count_and_is_larger() -> None:
    """Returns a larger number with the same number of 1 bits, every time."""
    for n in (3, 12, 255, 256, 1000, 65535, 2**40 + 2**20):
        found = next_with_same_bits(n)
        assert found > n
        assert ones(found) == ones(n)


def test_agrees_with_counting_up() -> None:
    """Matches a number-by-number search for every n up to 5,000."""
    for n in range(1, 5001):
        assert next_with_same_bits(n) == by_counting_up(n), n


def test_chains_through_every_number_with_three_bits() -> None:
    """Visits every 12-bit number with three 1s, in order, when applied repeatedly."""
    expected = [n for n in range(1 << 12) if ones(n) == 3]
    visited = [expected[0]]
    while len(visited) < len(expected):
        visited.append(next_with_same_bits(visited[-1]))

    assert visited == expected


def test_does_not_count_up_from_a_huge_number() -> None:
    """Answers for numbers hundreds of bits long within the time limit.

    From 2**200 the next number with one bit is 2**201, and there are 2**200
    numbers in between.
    """
    assert next_with_same_bits(1 << 200) == 1 << 201
    block = ((1 << 100) - 1) << 100
    assert next_with_same_bits(block) == (1 << 200) | ((1 << 99) - 1)
    huge = (1 << 1999) | (0b1011 << 700)
    assert next_with_same_bits(huge) == (1 << 1999) | (0b1100 << 700) | 1
