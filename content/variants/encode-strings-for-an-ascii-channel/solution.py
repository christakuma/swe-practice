"""Reference solution. CI asserts this passes every test in `tests.py`."""


def encode(strings: list[str]) -> str:
    """Pack a list of arbitrary strings into one printable-ASCII string.

    Each string becomes a `|` followed by its code points in hexadecimal,
    separated by commas. Hex digits, the comma and the bar are all printable
    ASCII, and none of the three can be mistaken for another, so nothing has
    to be escaped.

    The bar is a prefix rather than a separator. That is what makes the
    empty list (no bars) different from a list of one empty string (one bar,
    nothing after it).
    """
    return "".join(
        "|" + ",".join(f"{ord(character):x}" for character in text) for text in strings
    )


def decode(encoded: str) -> list[str]:
    """Unpack a string produced by `encode`.

    Splitting on the bar gives one empty piece before the first bar and then
    one piece per string. An empty piece is an empty string, which splitting
    on the comma would otherwise turn into one empty number.
    """
    return [
        "".join(chr(int(code, 16)) for code in piece.split(",")) if piece else ""
        for piece in encoded.split("|")[1:]
    ]
