"""Your solution goes here. The tests import `fewest_words` from this module."""


def fewest_words(text: str, words: list[str]) -> int:
    """Return the fewest dictionary words that `text` splits into.

    Args:
        text: the string to split. May be empty.
        words: the dictionary. Words may be reused, and not all of them need
            be used.

    Returns:
        The smallest number of words whose concatenation is exactly `text`,
        or -1 if no sequence of dictionary words spells it. 0 for the empty
        string.
    """
    raise NotImplementedError
