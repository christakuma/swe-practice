"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import pairwise, product

from solution import Decoder, encode

AWKWARD = ["", "a", "12", ":", "3:abc", "\n", "\x00", "#,;|", "5", "é漢", "0:", "ab"]


def feed_in_pieces(text: str, cuts: list[int]) -> list[list[str]]:
    """What each call returns when `text` is cut at the given positions."""
    decoder = Decoder()
    edges = [0, *cuts, len(text)]
    return [decoder.feed(text[a:b]) for a, b in pairwise(edges)]


def flatten(batches: list[list[str]]) -> list[str]:
    return [string for batch in batches for string in batch]


def test_decodes_text_that_arrives_whole() -> None:
    """Returns every string when the encoded text is fed in one piece."""
    strings = ["hello", "world", ""]

    assert Decoder().feed(encode(strings)) == strings


def test_decodes_text_that_arrives_one_character_at_a_time() -> None:
    """Returns every string, once and in order, from single characters."""
    strings = ["hello", "", "world", "12:34"]
    decoder = Decoder()

    received = [
        string for character in encode(strings) for string in decoder.feed(character)
    ]

    assert received == strings


def test_returns_a_string_with_the_chunk_that_completes_it() -> None:
    """Hands over a string in the same call that delivers its last character.

    The first chunk is exactly the encoding of the first string, so nothing
    after it has arrived yet to say that it is finished.
    """
    first, second = encode(["alpha"]), encode(["beta"])
    decoder = Decoder()

    assert decoder.feed(first) == ["alpha"]
    assert decoder.feed(second[:-1]) == []
    assert decoder.feed(second[-1]) == ["beta"]


def test_returns_nothing_until_a_string_is_complete() -> None:
    """Returns an empty list for a chunk that finishes no string."""
    text = encode(["abcdefgh"])
    decoder = Decoder()

    assert decoder.feed(text[:-3]) == []
    assert decoder.feed("") == []
    assert decoder.feed(text[-3:]) == ["abcdefgh"]


def test_does_not_return_a_string_twice() -> None:
    """Returns each string from one call only."""
    text = encode(["a", "b", "c"])
    middle = len(text) // 2

    batches = feed_in_pieces(text, [middle])

    assert flatten(batches) == ["a", "b", "c"]


def test_a_cut_may_fall_inside_a_length() -> None:
    """Handles a chunk that ends part-way through a string's length.

    A string of 123 characters, cut at every position including between the
    digits of whatever says how long it is.
    """
    strings = ["x" * 123, "tail"]
    text = encode(strings)

    for cut in range(len(text) + 1):
        assert flatten(feed_in_pieces(text, [cut])) == strings, cut


def test_empty_strings_are_complete_at_once() -> None:
    """Returns empty strings without waiting for anything to follow them."""
    assert Decoder().feed(encode(["", "", ""])) == ["", "", ""]
    assert Decoder().feed(encode([""])) == [""]


def test_an_empty_list_produces_nothing() -> None:
    """Returns nothing for the encoding of an empty list."""
    decoder = Decoder()

    assert decoder.feed(encode([])) == []
    assert decoder.feed("") == []


def test_decoders_do_not_share_state() -> None:
    """Keeps two decoders' unfinished text apart."""
    text = encode(["shared"])
    one, two = Decoder(), Decoder()

    assert one.feed(text[:3]) == []
    assert two.feed(text) == ["shared"]
    assert one.feed(text[3:]) == ["shared"]


def test_survives_every_cut_of_every_awkward_pair() -> None:
    """Rebuilds every pair of awkward strings from every two-way and char-by-char cut.

    The strings include digits, the empty string, text that looks like an
    encoding, and whatever a format is likely to use as a separator.
    """
    for pair in product(AWKWARD, repeat=2):
        strings = list(pair)
        text = encode(strings)
        for cut in range(len(text) + 1):
            assert flatten(feed_in_pieces(text, [cut])) == strings, (strings, cut)
        every = list(range(1, len(text)))
        assert flatten(feed_in_pieces(text, every)) == strings, strings


def test_survives_three_way_cuts() -> None:
    """Rebuilds a list from every way of cutting its encoding into three."""
    strings = ["12", "", "3:4", "x"]
    text = encode(strings)

    for first in range(len(text) + 1):
        for second in range(first, len(text) + 1):
            assert flatten(feed_in_pieces(text, [first, second])) == strings


def test_handles_long_strings_in_small_chunks() -> None:
    """Rebuilds two thousand-character strings from chunks of seven characters."""
    strings = ["ab:" * 700, "9" * 2000, "", "\n" * 1500]
    text = encode(strings)
    decoder = Decoder()

    received = []
    for start in range(0, len(text), 7):
        received.extend(decoder.feed(text[start : start + 7]))

    assert received == strings
