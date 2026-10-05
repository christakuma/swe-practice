"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import is_palindrome


def reference(text: str) -> bool:
    """Filter, fold and compare with the reverse -- the banned O(n)-space way.

    An independent oracle: it never touches a pointer, so it shares no skip
    logic with a two-pointer solution.
    """
    cleaned = [character.lower() for character in text if character.isalnum()]
    return cleaned == cleaned[::-1]


def test_accepts_a_sentence_palindrome() -> None:
    """Ignores spaces, punctuation and case."""
    assert is_palindrome("A man, a plan, a canal: Panama") is True


def test_rejects_a_non_palindrome() -> None:
    """Reports False for a string that does not read both ways."""
    assert is_palindrome("race a car") is False


def test_handles_an_empty_string() -> None:
    """Reports True for an empty string."""
    assert is_palindrome("") is True


def test_handles_a_string_with_nothing_to_compare() -> None:
    """Reports True when no character counts.

    Both pointers have to skip past everything, which is where an unguarded
    skip loop runs off the end and raises IndexError.
    """
    assert is_palindrome(".,") is True
    assert is_palindrome("   ") is True
    assert is_palindrome("!!!!!!!") is True


def test_handles_a_single_character() -> None:
    """Reports True for one character, alphanumeric or not."""
    assert is_palindrome("a") is True
    assert is_palindrome("1") is True
    assert is_palindrome(".") is True


def test_ignores_case() -> None:
    """Folds case before comparing."""
    assert is_palindrome("Aa") is True
    assert is_palindrome("AbBa") is True
    assert is_palindrome("Ab") is False


def test_skips_runs_of_ignored_characters() -> None:
    """Skips several ignored characters in a row.

    A skip written as an `if` rather than a `while` advances one position and
    then compares punctuation against a letter.
    """
    assert is_palindrome("a,,,,a") is True
    assert is_palindrome("a....b") is False
    assert is_palindrome(",,,a,,,") is True


def test_handles_digits() -> None:
    """Treats digits as significant."""
    assert is_palindrome("12321") is True
    assert is_palindrome("12345") is False
    assert is_palindrome("a1a") is True
    assert is_palindrome("a1b") is False


def test_handles_both_parities() -> None:
    """Handles odd and even numbers of significant characters."""
    assert is_palindrome("aba") is True
    assert is_palindrome("abba") is True
    assert is_palindrome("abab") is False
    assert is_palindrome("abca") is False


def test_handles_non_ascii_letters() -> None:
    """Classifies and folds characters outside ASCII.

    An explicit a-z range check treats these as punctuation and skips them,
    which turns a non-palindrome into a palindrome.
    """
    assert is_palindrome("été") is True
    assert is_palindrome("Été") is True
    assert is_palindrome("éxé") is True
    assert is_palindrome("éab") is False


def test_returns_a_bool() -> None:
    """Returns True or False rather than a truthy value."""
    assert is_palindrome("aa") is True
    assert is_palindrome("ab") is False


def test_agrees_with_a_reference_on_every_short_string() -> None:
    """Matches the filter-and-reverse oracle for every string up to length seven.

    Built from one lowercase letter, its uppercase, a digit and two different
    ignorable characters, so every interleaving of significant and skippable
    positions appears -- about ninety thousand strings. The guard bugs and the
    if-instead-of-while bug each need a particular interleaving.
    """
    for length in range(8):
        for characters in product("aA1.,", repeat=length):
            text = "".join(characters)

            assert is_palindrome(text) is reference(text), text


def test_handles_a_long_string() -> None:
    """Checks a two-million character string within the time limit.

    The filtered-copy solution would allocate two more sequences this size to
    answer a one-bit question.

    The mismatch is introduced at the *front* rather than the centre: a single
    extra character in the exact middle of a palindrome leaves it a palindrome,
    which is a pleasant way to write a test that cannot fail.
    """
    half = "ab, " * 250_000

    assert is_palindrome(half + half[::-1]) is True
    assert is_palindrome("z" + half + half[::-1]) is False
