"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from solution import edit_distance


def test_measures_the_classic_pair() -> None:
    """Counts three edits between kitten and sitting."""
    assert edit_distance("kitten", "sitting") == 3


def test_counts_deletions_and_replacements_together() -> None:
    """Mixes deletions and replacements in one answer."""
    assert edit_distance("horse", "ros") == 3


def test_handles_an_empty_source() -> None:
    """Costs one insertion per character when the source is empty."""
    assert edit_distance("", "abc") == 3


def test_handles_an_empty_target() -> None:
    """Costs one deletion per character when the target is empty."""
    assert edit_distance("abc", "") == 3


def test_handles_two_empty_strings() -> None:
    """Costs nothing to turn nothing into nothing."""
    assert edit_distance("", "") == 0


def test_handles_identical_strings() -> None:
    """Costs nothing when the strings already match."""
    assert edit_distance("same", "same") == 0


def test_counts_a_transposition_as_two_edits() -> None:
    """Charges two edits for a swapped pair.

    Levenshtein has no transposition operation, so `ab` to `ba` is two
    replacements. Damerau-Levenshtein charges one, and the difference is a
    specification choice rather than a bug.
    """
    assert edit_distance("ab", "ba") == 2


def test_handles_a_shared_middle() -> None:
    """Finds the cheap answer when the strings overlap in the middle."""
    assert edit_distance("flaw", "lawn") == 2


def test_handles_a_longer_pair() -> None:
    """Measures a longer pair with several kinds of edit."""
    assert edit_distance("intention", "execution") == 5


def test_is_symmetric() -> None:
    """Gives the same answer whichever string is the source.

    Insertion and deletion are mirror images, so the distance is symmetric. A
    solution that handles only one of the two directions passes the earlier
    tests and fails here.
    """
    assert edit_distance("sitting", "kitten") == 3
    assert edit_distance("ros", "horse") == 3


def test_handles_long_strings_quickly() -> None:
    """Measures two strings long enough to need the table.

    Three hundred characters each, sharing nothing: ninety thousand cells. The
    exponential recursion over three choices per character does not finish.
    """
    assert edit_distance("a" * 300, "b" * 300) == 300
