"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.

Almost every test here is a **round trip** rather than a comparison against an
expected encoding. The format is the solver's to choose, so the only thing that
can be asserted is the property the prompt actually requires:
`decode(encode(x)) == x`.
"""

from itertools import product

from solution import decode, encode

NASTY = ["", ":", "0", "a", "00:", ":0", "\\", "\n", "#", "1:"]


def roundtrip(strings: list[str]) -> list[str]:
    """Encode then decode, which must be the identity."""
    return decode(encode(strings))


def test_round_trips_ordinary_strings() -> None:
    """Recovers a simple list unchanged."""
    assert roundtrip(["hello", "world"]) == ["hello", "world"]


def test_round_trips_an_empty_list() -> None:
    """Recovers an empty list as an empty list.

    The classic separator-format bug: `"".split(",")` returns `[""]`, so a
    join-based encoding cannot tell no strings from one empty string.
    """
    assert roundtrip([]) == []


def test_round_trips_a_single_empty_string() -> None:
    """Recovers a list holding one empty string.

    The other half of the pair above. These two must come back different, and
    a separator format makes them identical.
    """
    assert roundtrip([""]) == [""]


def test_distinguishes_no_strings_from_one_empty_string() -> None:
    """Encodes the empty list and [""] to different strings.

    Stated directly rather than only via the round trips, because this is the
    one place the format itself is constrained: if these two encode to the same
    text, no decoder can separate them.
    """
    assert encode([]) != encode([""])


def test_round_trips_several_empty_strings() -> None:
    """Recovers the right number of empty strings."""
    assert roundtrip(["", ""]) == ["", ""]
    assert roundtrip(["", "", ""]) == ["", "", ""]
    assert roundtrip(["a", "", "b"]) == ["a", "", "b"]


def test_round_trips_strings_containing_likely_separators() -> None:
    """Survives payloads holding the characters a format might reserve."""
    for character in (",", ":", ";", "#", "|", "/", "\\", " ", "\t"):
        assert roundtrip([character]) == [character], character
        assert roundtrip(["a" + character + "b", "c"]) == [
            "a" + character + "b",
            "c",
        ], character


def test_round_trips_strings_containing_newlines() -> None:
    """Survives payloads holding newlines and carriage returns."""
    assert roundtrip(["\n"]) == ["\n"]
    assert roundtrip(["a\nb", "c\r\nd"]) == ["a\nb", "c\r\nd"]
    assert roundtrip(["\n", "\n"]) == ["\n", "\n"]


def test_round_trips_strings_containing_digits_and_colons() -> None:
    """Survives payloads that look like a length prefix.

    A length-prefixed format writes digits and a terminator, so a payload of
    "2:hi" is the natural attack on it. The decoder must not read a length out
    of the payload -- it was told how many characters to take.
    """
    assert roundtrip(["2:hi"]) == ["2:hi"]
    assert roundtrip(["0:"]) == ["0:"]
    assert roundtrip(["999"]) == ["999"]
    assert roundtrip(["1:a", "2:bb"]) == ["1:a", "2:bb"]


def test_round_trips_a_payload_that_is_itself_an_encoding() -> None:
    """Survives a payload that is a complete valid encoding of something else.

    The strongest version of the attack: the inner text is not merely
    separator-shaped, it is a well-formed message. A decoder that parses rather
    than counts unpacks the inner list and returns the wrong thing.
    """
    inner = encode(["nested", "payload"])

    assert roundtrip([inner]) == [inner]
    assert roundtrip([inner, "after"]) == [inner, "after"]


def test_round_trips_null_bytes() -> None:
    """Survives payloads holding a null byte."""
    assert roundtrip(["\x00"]) == ["\x00"]
    assert roundtrip(["a\x00b", "\x00"]) == ["a\x00b", "\x00"]


def test_round_trips_non_ascii() -> None:
    """Survives payloads outside ASCII."""
    assert roundtrip(["é", "日本語", "🙂"]) == ["é", "日本語", "🙂"]


def test_round_trips_a_single_string() -> None:
    """Recovers a one-element list without a trailing empty string.

    A format that writes a separator after every string, rather than between
    them, decodes to ["a", ""] here.
    """
    assert roundtrip(["a"]) == ["a"]
    assert roundtrip(["abc"]) == ["abc"]


def test_round_trips_long_strings() -> None:
    """Survives payloads whose lengths need several digits.

    A fixed-width length field overflows here; the terminator is what lets the
    length be any number of digits.
    """
    assert roundtrip(["a" * 1_000]) == ["a" * 1_000]
    assert roundtrip(["a" * 100_000, "b"]) == ["a" * 100_000, "b"]
    assert roundtrip(["x" * 9, "y" * 10, "z" * 100]) == ["x" * 9, "y" * 10, "z" * 100]


def test_round_trips_many_strings() -> None:
    """Survives a list of ten thousand strings."""
    strings = [str(value) for value in range(10_000)]

    assert roundtrip(strings) == strings


def test_encode_returns_a_string_and_decode_a_list() -> None:
    """Returns the declared types."""
    assert type(encode(["a"])) is str
    assert type(decode(encode(["a"]))) is list


def test_round_trips_every_short_list_of_nasty_strings() -> None:
    """Round trips every list of up to three adversarial fragments.

    The fragments are the empty string, a terminator, a digit, a letter, and
    several combinations that look like length prefixes -- so every way a
    payload can impersonate the format's own syntax appears, in every position.
    About a thousand lists.
    """
    for length in range(4):
        for fragments in product(NASTY, repeat=length):
            strings = list(fragments)

            assert roundtrip(strings) == strings, strings


def test_round_trips_concatenations_of_nasty_strings() -> None:
    """Round trips single strings built by concatenating adversarial fragments.

    The sweep above varies the list; this one varies the payload, so a decoder
    that gets confused mid-payload rather than at a boundary is caught too.
    """
    for parts in product(NASTY, repeat=3):
        payload = "".join(parts)

        assert roundtrip([payload]) == [payload], payload
        assert roundtrip([payload, "tail"]) == [payload, "tail"], payload


def test_does_not_reserve_any_character() -> None:
    """Round trips every single code point in a wide range, one at a time.

    If the format reserves a character, this is where it shows up: the
    offending one comes back altered or splits a payload in two.
    """
    for code_point in range(1, 1_200):
        character = chr(code_point)

        assert roundtrip([character]) == [character], code_point
        assert roundtrip([character, character]) == [character, character], code_point
