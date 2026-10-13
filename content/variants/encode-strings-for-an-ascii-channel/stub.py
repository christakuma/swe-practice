"""Your solution goes here. The tests import from this module."""


def encode(strings: list[str]) -> str:
    """Pack a list of arbitrary strings into one printable-ASCII string.

    Args:
        strings: the strings to pack. Any contents at all.

    Returns:
        A string of characters in the range 32..126 from which `decode`
        recovers the original list.
    """
    raise NotImplementedError


def decode(encoded: str) -> list[str]:
    """Unpack a string produced by `encode`.

    Args:
        encoded: the output of `encode`.

    Returns:
        The original list of strings, exactly.
    """
    raise NotImplementedError
