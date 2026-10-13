"""Reference solution. CI asserts this passes every test in `tests.py`."""

SEPARATOR = ":"


def encode(strings: list[str]) -> str:
    """Pack a list of strings into a single string.

    Each string is written as its length, a colon, and then its characters.
    The decoder never searches the characters for anything -- it counts them
    -- so they may be anything at all.
    """
    return "".join(f"{len(string)}{SEPARATOR}{string}" for string in strings)


class Decoder:
    """Rebuilds strings from encoded text that arrives a piece at a time.

    Two pieces of state survive between calls: the text that has arrived and
    not been used, and -- if a length has been read -- how many characters the
    current string still needs. A chunk can end while either is incomplete,
    and the next call picks up exactly there.

    A string is emitted as soon as the unused text holds all of it, which for
    an empty string is the moment its length is known.
    """

    def __init__(self) -> None:
        """Create a decoder that has received nothing yet."""
        self._unused = ""
        self._length: int | None = None

    def feed(self, chunk: str) -> list[str]:
        """Accept the next piece of encoded text."""
        self._unused += chunk
        completed: list[str] = []
        position = 0
        while True:
            if self._length is None:
                separator = self._unused.find(SEPARATOR, position)
                if separator < 0:
                    break
                self._length = int(self._unused[position:separator])
                position = separator + 1
            if len(self._unused) - position < self._length:
                break
            completed.append(self._unused[position : position + self._length])
            position += self._length
            self._length = None
        self._unused = self._unused[position:]
        return completed
