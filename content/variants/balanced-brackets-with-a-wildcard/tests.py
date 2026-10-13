"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import is_balanced


def plainly_balanced(text: str) -> bool:
    """The ordinary check, for a string with no stars left in it."""
    depth = 0
    for character in text:
        depth += 1 if character == "(" else -1
        if depth < 0:
            return False
    return depth == 0


def by_every_reading(text: str) -> bool:
    """Try each star as an opener, a closer and nothing."""
    stars = text.count("*")
    for reading in product(("(", ")", ""), repeat=stars):
        chosen = iter(reading)
        candidate = "".join(next(chosen) if c == "*" else c for c in text)
        if plainly_balanced(candidate):
            return True
    return False


def test_reads_a_star_as_nothing() -> None:
    """Accepts a string that balances when its star is ignored."""
    assert is_balanced("(*)") is True


def test_reads_a_star_as_an_opener_or_a_closer() -> None:
    """Accepts strings that need a star to be a bracket."""
    assert is_balanced("(*))") is True
    assert is_balanced("((*)") is True


def test_still_checks_strings_with_no_stars() -> None:
    """Gives the ordinary answer when there are no stars."""
    assert is_balanced("(())()") is True
    assert is_balanced("(()") is False
    assert is_balanced(")(") is False
    assert is_balanced("") is True


def test_a_star_cannot_close_what_opens_after_it() -> None:
    """Rejects an opener that only an earlier star could have closed."""
    assert is_balanced("*(") is False
    assert is_balanced("(*(") is False


def test_a_star_cannot_open_what_closed_before_it() -> None:
    """Rejects a closer that only a later star could have opened."""
    assert is_balanced(")*") is False
    assert is_balanced(")*(") is False


def test_reads_different_stars_differently() -> None:
    """Uses one star as an opener and another as a closer in the same string."""
    assert is_balanced("*)(*") is True
    assert is_balanced("**") is True
    assert is_balanced("*") is True


def test_agrees_with_trying_every_reading() -> None:
    """Matches a try-every-reading search for every string up to length seven."""
    for length in range(8):
        for letters in product("()*", repeat=length):
            text = "".join(letters)
            assert is_balanced(text) is by_every_reading(text), text


def test_checks_a_hundred_thousand_characters() -> None:
    """Checks a long string of stars within the time limit.

    Fifty thousand stars are three to the fifty-thousandth readings. Here
    they can absorb fifty thousand closers, and then cannot absorb one more.
    """
    half = 50_000

    assert is_balanced("*" * half + ")" * half) is True
    assert is_balanced("*" * half + ")" * (half + 1)) is False
