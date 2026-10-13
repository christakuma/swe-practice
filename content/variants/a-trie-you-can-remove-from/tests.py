"""The hidden test suite.

Each test's docstring becomes the label on its `CheckReport`.
"""

from itertools import product

from solution import Trie

WORDS = ("", "a", "ab", "b")
PROBES = ("", "a", "ab", "abc", "b", "ba")


def test_removes_a_word() -> None:
    """Reports a removed word as absent, and its prefixes as gone."""
    trie = Trie()
    trie.insert("apple")

    assert trie.remove("apple") is True
    assert trie.contains("apple") is False
    assert trie.starts_with("app") is False
    assert trie.starts_with("") is False


def test_removing_a_prefix_keeps_the_longer_word() -> None:
    """Leaves a longer word in place when its prefix is removed."""
    trie = Trie()
    trie.insert("apple")
    trie.insert("app")
    trie.remove("app")

    assert trie.contains("app") is False
    assert trie.contains("apple") is True
    assert trie.starts_with("app") is True


def test_removing_a_longer_word_keeps_its_prefix() -> None:
    """Leaves a stored prefix in place when the longer word is removed."""
    trie = Trie()
    trie.insert("apple")
    trie.insert("app")
    trie.remove("apple")

    assert trie.contains("app") is True
    assert trie.starts_with("appl") is False


def test_removing_a_sibling_keeps_the_shared_prefix() -> None:
    """Keeps a prefix that another word still uses."""
    trie = Trie()
    trie.insert("car")
    trie.insert("cat")
    trie.remove("car")

    assert trie.starts_with("ca") is True
    assert trie.contains("cat") is True
    assert trie.starts_with("car") is False


def test_reports_whether_anything_was_removed() -> None:
    """Returns False for a word that is not stored, and changes nothing."""
    trie = Trie()
    trie.insert("apple")

    assert trie.remove("app") is False
    assert trie.remove("pear") is False
    assert trie.contains("apple") is True
    assert trie.starts_with("app") is True
    assert trie.remove("apple") is True
    assert trie.remove("apple") is False


def test_a_word_can_be_put_back() -> None:
    """Stores a word again after it has been removed."""
    trie = Trie()
    trie.insert("go")
    trie.remove("go")
    trie.insert("go")
    trie.insert("go")

    assert trie.contains("go") is True
    assert trie.remove("go") is True
    assert trie.starts_with("g") is False


def test_agrees_with_a_set_for_every_short_history() -> None:
    """Matches a set-of-words model after every sequence of five operations."""
    operations = [(kind, word) for kind in ("insert", "remove") for word in WORDS]
    for history in product(operations, repeat=5):
        trie, model = Trie(), set()
        for kind, word in history:
            if kind == "insert":
                trie.insert(word)
                model.add(word)
            else:
                assert trie.remove(word) is (word in model), history
                model.discard(word)
        for probe in PROBES:
            assert trie.contains(probe) is (probe in model), (history, probe)
            expected = any(word.startswith(probe) for word in model)
            assert trie.starts_with(probe) is expected, (history, probe)


def test_answers_without_looking_at_every_word() -> None:
    """Answers twenty thousand prefix queries against fifty thousand words.

    Every query is for a prefix nothing has, which is the worst case for a
    structure that has to check each stored word in turn: a set of strings
    makes a billion comparisons here, and a trie follows one short path.
    """
    trie = Trie()
    for index in range(50_000):
        trie.insert(f"{index:05d}")

    for index in range(20_000):
        assert trie.starts_with(f"x{index:04d}") is False
    assert trie.starts_with("4999") is True


def test_handles_many_insertions_and_removals() -> None:
    """Inserts and removes fifty thousand words within the time limit."""
    trie = Trie()
    words = [f"{index:05d}" for index in range(50_000)]
    for word in words:
        trie.insert(word)
    for word in words[::2]:
        assert trie.remove(word) is True

    assert trie.contains("00001") is True
    assert trie.contains("00002") is False
    assert trie.starts_with("0000") is True
    for word in words[1::2]:
        trie.remove(word)
    assert trie.starts_with("") is False
