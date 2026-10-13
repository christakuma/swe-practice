"""Your solution goes here.

The tests import `encode` and `Decoder` from this module.
"""


def encode(strings: list[str]) -> str:
    """Pack a list of strings into a single string.

    Args:
        strings: the strings to pack. Any contents, including empty strings
            and any character at all.

    Returns:
        A single string that a `Decoder` can turn back into the list, however
        it is cut into pieces on the way.
    """
    raise NotImplementedError


class Decoder:
    """Rebuilds strings from encoded text that arrives a piece at a time."""

    def __init__(self) -> None:
        """Create a decoder that has received nothing yet."""
        raise NotImplementedError

    def feed(self, chunk: str) -> list[str]:
        """Accept the next piece of encoded text.

        Args:
            chunk: the next characters of the output of `encode`. May be
                empty, and may end anywhere.

        Returns:
            The strings whose last character arrived in this chunk, in order.
        """
        raise NotImplementedError
