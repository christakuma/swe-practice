"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import reverse_bytes


def by_conversion(n: int) -> int:
    return int.from_bytes(n.to_bytes(4, "big"), "little")


def test_reverses_four_distinct_bytes() -> None:
    """Reverses the order of four different bytes."""
    assert reverse_bytes(0x12345678) == 0x78563412


def test_keeps_the_bits_inside_each_byte() -> None:
    """Moves bytes whole rather than reversing their bits."""
    assert reverse_bytes(0x00000001) == 0x01000000
    assert reverse_bytes(0x80000000) == 0x00000080


def test_moves_each_byte_to_its_mirror_position() -> None:
    """Sends each of the four byte positions to the right place."""
    assert reverse_bytes(0x000000AB) == 0xAB000000
    assert reverse_bytes(0x0000AB00) == 0x00AB0000
    assert reverse_bytes(0x00AB0000) == 0x0000AB00
    assert reverse_bytes(0xAB000000) == 0x000000AB


def test_handles_the_extremes() -> None:
    """Leaves zero and all-ones unchanged."""
    assert reverse_bytes(0) == 0
    assert reverse_bytes(0xFFFFFFFF) == 0xFFFFFFFF


def test_applying_it_twice_restores_the_value() -> None:
    """Returns the original value when applied twice."""
    for n in (0x12345678, 0xDEADBEEF, 1, 0xFF00FF00, 0x0A0B0C0D):
        assert reverse_bytes(reverse_bytes(n)) == n


def test_agrees_with_a_byte_conversion() -> None:
    """Matches an independent byte-order conversion across the range."""
    for n in range(0, 2**32, 9_999_991):
        assert reverse_bytes(n) == by_conversion(n), hex(n)
    for n in range(4096):
        assert reverse_bytes(n) == by_conversion(n), hex(n)


def test_stays_within_thirty_two_bits() -> None:
    """Returns a value that fits in 32 bits."""
    assert 0 <= reverse_bytes(0xFFFFFFFF) < 2**32
    assert 0 <= reverse_bytes(0x000000FF) < 2**32
