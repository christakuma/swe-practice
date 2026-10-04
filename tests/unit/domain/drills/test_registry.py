"""The drill vocabulary, and the property that makes it a vocabulary and not a list.

The cases that matter here are about the **boundary between the two registries**.
`domain/drills/registry.py` argues that they are deliberately two tables rather
than one keyed by name, and the argument only holds if the vocabularies are
actually disjoint — so that is asserted directly rather than trusted, because the
failure mode is silent: a drill naming a git assertion would validate, then reach
a dispatcher holding the wrong kind of query.
"""

from __future__ import annotations

from practice.domain.checks import registry as git_registry
from practice.domain.drills import registry as drill_registry
from tests.fakes.drill import FakeDrillQuery, a_result
from tests.unit.domain.drills.helpers import run


def test_every_registered_name_has_a_function() -> None:
    """So a name can never be added to the legal set without something to run."""
    assert set(drill_registry.DRILL_ASSERTIONS) == set(drill_registry.DRILL_CHECKS)
    assert all(callable(fn) for fn in drill_registry.DRILL_CHECKS.values())


def test_there_are_ten_of_them() -> None:
    """A literal count, which is the §13 rule made visible.

    Phase 11 deleted `reflog_contains` and `command_count` from the git family
    because 24 scenarios wanted neither. The same standard applies here, and
    `tests/content/test_drills.py` is where it is enforced against the library —
    this is just the number, so that growing the vocabulary is a deliberate edit
    to a test rather than a thing that happens.
    """
    assert len(drill_registry.DRILL_ASSERTIONS) == 10


def test_the_two_families_partition_the_vocabulary() -> None:
    both = drill_registry.CRAFT_ASSERTIONS | drill_registry.STATE_ASSERTIONS

    assert both == drill_registry.DRILL_ASSERTIONS
    assert not (drill_registry.CRAFT_ASSERTIONS & drill_registry.STATE_ASSERTIONS)


def test_the_drill_and_git_vocabularies_do_not_overlap() -> None:
    """The property the two-registry design rests on.

    If a name were in both, the schema could not tell which dispatcher an
    exercise meant, and the one that ran would be holding the wrong port.
    """
    assert not (drill_registry.DRILL_ASSERTIONS & git_registry.ASSERTIONS)


def test_a_git_assertion_is_not_registered_for_a_drill() -> None:
    assert git_registry.is_registered("tree_equals")
    assert not drill_registry.is_registered("tree_equals")


def test_a_drill_assertion_is_not_registered_for_a_scenario() -> None:
    assert drill_registry.is_registered("table_matches")
    assert not git_registry.is_registered("table_matches")


def test_a_cross_family_name_gets_no_suggestion_and_that_is_correct() -> None:
    """The Phase 14 finding, pinned so it cannot be quietly "fixed".

    The plan was that `tree_equals` in a drill would be offered `table_matches`.
    It is not, and should not be: the threshold was measured against the git
    vocabulary, where a real typo scores 0.33 and up, and a name from another
    family shares almost no trigrams with anything. Lowering the threshold to
    catch this would make every unknown name produce three irrelevant
    suggestions.
    """
    assert drill_registry.suggest("tree_equals") == ()


def test_a_cross_family_name_is_named_rather_than_guessed_at() -> None:
    """What replaced the guess. A known fact beats a similarity score."""
    assert drill_registry.other_family("tree_equals") == "git_scenario"
    assert drill_registry.misplaced_in_scenario("table_matches") == "sql_drill"


def test_a_name_in_its_own_family_is_not_reported_as_misplaced() -> None:
    assert drill_registry.other_family("table_matches") is None
    assert drill_registry.misplaced_in_scenario("tree_equals") is None


def test_a_name_in_neither_family_is_not_reported_as_misplaced() -> None:
    """A plain typo falls through to `suggest`, which is what it is for."""
    assert drill_registry.other_family("tabel_matches") is None
    assert drill_registry.misplaced_in_scenario("tree_equal") is None


def test_suggestions_are_drawn_only_from_the_drill_vocabulary() -> None:
    for name in ("tree_equals", "result_match", "table_row_counts"):
        assert set(drill_registry.suggest(name)) <= drill_registry.DRILL_ASSERTIONS


def test_a_near_miss_finds_its_target() -> None:
    assert drill_registry.suggest("result_match")[0] == "result_matches"
    assert drill_registry.suggest("table_rows_count")[0] == "table_row_count"


def test_an_unrelated_word_gets_no_suggestions() -> None:
    """A suggestion list that fires on everything trains the reader to ignore it."""
    assert drill_registry.suggest("vacuum") == ()


def test_negation_is_applied_in_one_place_for_this_family_too() -> None:
    """§6.3's rule, holding over the second vocabulary -- which is better evidence
    that it was the right call than the original argument for it.
    """
    report = run(
        "table_exists", FakeDrillQuery(tables={}), table="orders", negated=True
    )

    assert report.passed
    assert (report.expected or "").startswith("not ")


def test_the_authors_words_are_carried_across_by_the_dispatcher() -> None:
    """So no assertion can forget to, and none has to know how."""
    report = run("result_row_count", FakeDrillQuery(result=a_result()), equals=2)

    assert report.check_id == "a-check"
    assert report.label == "The label the author wrote."
    assert report.explanation == "Why it matters."
