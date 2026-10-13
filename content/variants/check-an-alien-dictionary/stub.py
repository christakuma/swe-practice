"""Your solution goes here. The tests import from this module."""


def is_sorted(words: list[str], alphabet: str) -> bool:
    """Return whether `words` is in order under the given alphabet.

    Args:
        words: the words to check. May be empty, and may repeat.
        alphabet: every character in use, once each, in ascending order.

    Returns:
        True if each word is no later than the next, where a word precedes
        any longer word it is a prefix of.
    """
    raise NotImplementedError
