"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import decode, encode

FRAGMENTS = ["", "|", ",", "a", "7c", "é", "\n", "\x00", "😀", " ", "~", "\x7f"]


def printable(text: str) -> bool:
    return all(32 <= ord(character) <= 126 for character in text)


def test_recovers_a_simple_list() -> None:
    """Recovers a list of plain words unchanged."""
    assert decode(encode(["hello", "world"])) == ["hello", "world"]


def test_recovers_characters_outside_ascii() -> None:
    """Recovers accented letters and emoji."""
    strings = ["héllo", "wörld", "日本語", "😀👍"]

    assert decode(encode(strings)) == strings


def test_emits_only_printable_ascii() -> None:
    """Produces nothing outside the range 32 to 126."""
    strings = ["naïve", "line\nbreak", "\x00", "tab\there", "\x7f", "😀"]

    assert printable(encode(strings))
    assert decode(encode(strings)) == strings


def test_does_not_pass_control_characters_through() -> None:
    """Represents a newline and a null rather than emitting them."""
    assert "\n" not in encode(["a\nb"])
    assert "\x00" not in encode(["\x00"])


def test_tells_an_empty_list_from_an_empty_string() -> None:
    """Recovers [], [""] and ["", ""] as three different lists."""
    assert decode(encode([])) == []
    assert decode(encode([""])) == [""]
    assert decode(encode(["", ""])) == ["", ""]
    assert len({encode([]), encode([""]), encode(["", ""])}) == 3


def test_returns_strings_and_lists() -> None:
    """Returns a str from encode and a list from decode."""
    assert isinstance(encode(["a"]), str)
    assert isinstance(decode(encode(["a"])), list)


def test_round_trips_every_list_of_awkward_fragments() -> None:
    """Round trips every list of up to three awkward fragments, in ASCII."""
    for size in range(4):
        for chosen in product(FRAGMENTS, repeat=size):
            strings = list(chosen)
            packed = encode(strings)
            assert printable(packed), strings
            assert decode(packed) == strings, strings


def test_round_trips_every_code_point_in_a_wide_range() -> None:
    """Round trips single characters across the Basic Multilingual Plane."""
    for code in range(0, 0x10000, 7):
        strings = [chr(code), "x" + chr(code)]
        assert decode(encode(strings)) == strings, hex(code)


def test_handles_a_large_list() -> None:
    """Round trips ten thousand strings within the time limit."""
    strings = [f"item {index} é\n" for index in range(10_000)]

    assert decode(encode(strings)) == strings
