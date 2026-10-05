"""Your solution goes here.

The tests import both `encode` and `decode` from this module.
"""


def encode(strings: list[str]) -> str:
    """Pack a list of arbitrary strings into one string.

    Args:
        strings: the strings to pack. Any contents, including empty strings
            and any character at all.

    Returns:
        A single string from which `decode` recovers the original list.
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
