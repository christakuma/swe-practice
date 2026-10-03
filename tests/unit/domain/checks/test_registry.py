"""The assertion vocabulary, as a set of names.

These tests are deliberately about the *contract* of the registry rather than its
contents: a test that restates the 20 names in a second list only proves someone
typed them twice. The two that do pin content are the ones whose value comes from
being pinned — the count, and the fact that every assertion the shipped exercises
already use is registered.
"""

from __future__ import annotations

import pytest

from practice.domain.checks import registry

#: PLAN.md §6.3 enumerates the vocabulary in five groups. The number is asserted
#: rather than derived so that adding an assertion is a deliberate act with a
#: failing test attached, not something that happens by autocomplete.
#:
#: Twenty-two until Phase 11, which deleted `reflog_contains` and `command_count`
#: after twenty-four git scenarios wanted neither — so this test is also the
#: tripwire on *removing* one, and it fired as intended.
VOCABULARY_SIZE = 20


def test_the_vocabulary_is_the_size_the_plan_enumerates() -> None:
    assert len(registry.ASSERTIONS) == VOCABULARY_SIZE


def test_the_groups_partition_the_vocabulary() -> None:
    """Process assertions read the attempt log; content assertions read the repo.

    Phase 5 dispatches on exactly this split — one family takes a `RepoQuery` and
    the other takes an `Attempt` — so an assertion in both or in neither is a
    function nobody can call.
    """
    assert registry.CONTENT_ASSERTIONS | registry.PROCESS_ASSERTIONS == (
        registry.ASSERTIONS
    )
    assert not (registry.CONTENT_ASSERTIONS & registry.PROCESS_ASSERTIONS)


@pytest.mark.parametrize(
    "name",
    [
        # Every assertion the two shipped git scenarios use. If one of these ever
        # falls out of the registry, both exercises stop validating — better to
        # find out here, in a test that names the reason.
        "command_used",
        "head_detached",
        "is_ancestor",
        "ref_points_at",
        "ref_unchanged",
        "tree_equals",
        "worktree_clean",
    ],
)
def test_the_shipped_exercises_assertions_are_registered(name: str) -> None:
    assert registry.is_registered(name)


@pytest.mark.parametrize("name", ["tree_equal", "", "TREE_EQUALS", "revert"])
def test_an_unregistered_name_is_rejected(name: str) -> None:
    assert not registry.is_registered(name)


# --- suggestions -----------------------------------------------------------


@pytest.mark.parametrize(
    ("typo", "expected"),
    [
        ("tree_equal", "tree_equals"),
        ("tree_equalss", "tree_equals"),
        ("worktree_cleen", "worktree_clean"),
        ("branch_exist", "branch_exists"),
        # Word order reversed. This is the case plain edit distance loses, and
        # the reason the matcher is on trigrams.
        ("equals_tree", "tree_equals"),
    ],
)
def test_a_near_miss_suggests_the_name_it_missed(typo: str, expected: str) -> None:
    assert expected in registry.suggest(typo)


def test_a_name_with_nothing_close_suggests_nothing() -> None:
    """A suggestion list that fires on everything trains the reader to skip it."""
    assert registry.suggest("completely-unrelated-nonsense") == ()


def test_an_empty_name_suggests_nothing_rather_than_everything() -> None:
    assert registry.suggest("") == ()


def test_suggestions_are_capped_and_ordered_best_first() -> None:
    suggestions = registry.suggest("ref_points", limit=2)

    assert len(suggestions) <= 2
    assert suggestions[0] == "ref_points_at"


def test_an_exact_name_suggests_itself() -> None:
    """Not a use case, but a matcher that fails its own identity case is broken
    in a way that would only show up as mediocre suggestions elsewhere.
    """
    assert registry.suggest("stash_count")[0] == "stash_count"
