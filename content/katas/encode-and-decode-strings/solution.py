"""Reference solution. CI asserts this passes every test in `tests.py`."""


def encode(strings: list[str]) -> str:
    """Pack a list of arbitrary strings into one string.

    Length prefixing, which is the answer to the whole problem: each string is
    preceded by its length in decimal and a `:`.

        ["hi", ""]  ->  "2:hi0:"

    The `:` is **not a separator** -- that distinction is the kata. A separator
    sits between payloads and the decoder has to search for it, which is
    exactly what arbitrary payloads make impossible. This `:` terminates the
    *length*, and a length is digits only, so the terminator cannot occur
    inside the thing it terminates. A payload is free to contain colons,
    newlines, digits, nulls or a complete valid encoding of something else; the
    decoder never looks at the payload at all, it counts.

    That is why no character has to be reserved and nothing needs escaping.
    """
    return "".join(f"{len(string)}:{string}" for string in strings)


def decode(encoded: str) -> list[str]:
    """Unpack a string produced by `encode`.

    Read digits until the `:`, convert, then take exactly that many characters
    whatever they are. The payload is never scanned, only skipped -- so there
    is no state machine, no escape handling, and no input that can confuse it.

    `index` walks forward monotonically and each character is visited a
    constant number of times, so this is linear in the total length.

    The empty list and the list of empty strings both fall out with no special
    case: "" has no digits to read so the loop never runs, and "0:" yields one
    empty slice. Those two are the cases that break almost every ad-hoc format
    -- `"".split(",")` returns `[""]` rather than `[]`, which is the classic
    bug this format does not have.
    """
    strings: list[str] = []
    index = 0
    while index < len(encoded):
        colon = encoded.index(":", index)
        length = int(encoded[index:colon])
        start = colon + 1
        strings.append(encoded[start : start + length])
        index = start + length
    return strings
