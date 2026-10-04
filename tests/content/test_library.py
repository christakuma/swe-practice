"""Every exercise on disk, checked one by one.

The suite PLAN.md §9 describes as the thing that keeps a seventy-exercise
library honest. It is parametrized over the real `content/` directory rather
than over fixtures, so adding an exercise adds test cases without touching this
file — which is the content-as-data bet in §5, applied to its own tests.

**It shares its logic with `practice validate` on purpose.** Both call
`validate_library`, so a rule enforced in CI and a rule reported at the command
line cannot drift apart. What this file adds is *granularity* — a failure names
the exercise and the rule, which is what you want from a CI log you are reading
three days later — and the rules that are about a *good* exercise rather than a
loadable one, which PLAN.md §4.2 deliberately keeps out of the domain and the
schema both.

**The kind-specific cases are parametrized per kind rather than skipped.** An
`isinstance` check and a `pytest.skip` reads fine at three exercises and prints
a hundred and fifty skip lines at seventy. Partitioning is done defensively, so
an exercise that will not load lands in neither bucket and is reported by
`test_it_validates` instead of crashing collection.

**Half of §9's list is not here, and the gap is the point.** This file covers
everything checkable without running anything; `test_fixtures.py` covers what
needs the sandbox, which is why the two are separate.
`test_the_unproven_guarantees_are_still_unproven` is the tripwire over the
remainder: when the Phase 5 engine lands it fails, and someone has to come back
and write the grading tests rather than quietly leaving them undone.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.content import (
    ContentError,
    FilesystemContentRepository,
    load_exercise,
    validate_exercise,
    validate_library,
)
from practice.adapters.content.curriculum import load_curriculum
from practice.adapters.content.validation import discover, unproven_by_design
from practice.config import content_root
from practice.domain.checks import registry
from practice.domain.commands import parse_command_list
from practice.domain.exercise import (
    ExerciseKind,
    GitScenarioSpec,
    KataSpec,
)
from practice.interface.web.routes.dashboard import QUEUE_LIMIT

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.exercise import Exercise, ExerciseSpec

CONTENT_ROOT = content_root()

#: Every exercise directory, collected once at import time.
EXERCISE_DIRECTORIES = sorted(discover(CONTENT_ROOT))

#: The minimum a library has to hold for this suite to mean anything. Phase 2
#: ships one kata and two git scenarios (PLAN.md §11); the count only goes up.
MINIMUM_EXERCISES = 3


def _identify(directory: Path) -> str:
    """`git/revert-a-pushed-commit`, so a failure names the exercise."""
    return directory.relative_to(CONTENT_ROOT).as_posix()


def _of_kind(spec_type: type[ExerciseSpec]) -> list[Path]:
    """The directories whose exercise carries this kind of spec.

    Defensive about loading: a directory that will not load belongs to no kind,
    and `test_it_validates` is parametrized over every directory regardless, so
    it is still reported — as a test failure naming the problem rather than as
    an error during collection.
    """
    found = []
    for directory in EXERCISE_DIRECTORIES:
        try:
            exercise = load_exercise(directory)
        except ContentError:
            continue
        if isinstance(exercise.spec, spec_type):
            found.append(directory)
    return found


GIT_SCENARIO_DIRECTORIES = _of_kind(GitScenarioSpec)
KATA_DIRECTORIES = _of_kind(KataSpec)


@pytest.fixture(params=EXERCISE_DIRECTORIES, ids=_identify)
def exercise_directory(request: pytest.FixtureRequest) -> Path:
    directory: Path = request.param
    return directory


@pytest.fixture
def exercise(exercise_directory: Path) -> Exercise:
    return load_exercise(exercise_directory)


@pytest.fixture(params=GIT_SCENARIO_DIRECTORIES, ids=_identify)
def scenario_directory(request: pytest.FixtureRequest) -> Path:
    directory: Path = request.param
    return directory


@pytest.fixture
def scenario(scenario_directory: Path) -> GitScenarioSpec:
    spec = load_exercise(scenario_directory).spec
    assert isinstance(spec, GitScenarioSpec)
    return spec


@pytest.fixture(params=KATA_DIRECTORIES, ids=_identify)
def kata(request: pytest.FixtureRequest) -> KataSpec:
    spec = load_exercise(request.param).spec
    assert isinstance(spec, KataSpec)
    return spec


# --- the walk itself -------------------------------------------------------


def test_the_library_was_found() -> None:
    """Without this, every parametrized test below is vacuously true.

    The failure the architecture suite guards with
    `test_the_walk_actually_found_the_domain`: a wrong root or a renamed
    directory leaves a suite green forever while checking nothing at all, and a
    parametrized suite over an empty list is the quietest way there is to stop
    testing.
    """
    assert len(EXERCISE_DIRECTORIES) >= MINIMUM_EXERCISES


def test_both_tracks_are_represented() -> None:
    """Phase 2's deliverable is one kata *and* two git scenarios. A suite that
    only ever sees one kind proves nothing about the other's loader path — and
    would silently parametrize half of this file over nothing.
    """
    assert GIT_SCENARIO_DIRECTORIES
    assert KATA_DIRECTORIES


def test_the_whole_library_validates() -> None:
    """The same answer `practice validate` gives, as a test.

    Overlaps the per-exercise cases by design: this one also covers the
    library-level rules — a misplaced directory, an empty root — that no single
    exercise can fail.
    """
    report = validate_library(CONTENT_ROOT)

    assert report.ok, "\n".join(
        [
            *report.problems,
            *(
                f"{failure.name}: {problem}"
                for failure in report.failures
                for problem in failure.problems
            ),
        ]
    )


# --- every exercise --------------------------------------------------------


def test_it_validates(exercise_directory: Path) -> None:
    """Schema, referenced files, command-list legality, hints and notes."""
    report = validate_exercise(exercise_directory)

    assert report.ok, "\n".join(report.problems)


def test_its_id_matches_its_directory(
    exercise: Exercise, exercise_directory: Path
) -> None:
    """The id *is* the content path (PLAN.md §4.1)."""
    assert str(exercise.id) == _identify(exercise_directory)


def test_its_hints_are_progressive_rather_than_repeated(exercise: Exercise) -> None:
    """Hints are ordered and revealed one at a time (PLAN.md §4.3), so two
    identical ones spend a reveal on nothing.
    """
    texts = [hint.text.strip() for hint in exercise.hints]

    assert len(set(texts)) == len(texts)


def test_its_notes_are_worth_revealing(exercise: Exercise) -> None:
    """The notes are where the *why* lives, and the why is the product."""
    assert exercise.notes.strip()


# --- git scenarios ---------------------------------------------------------


def test_every_assertion_it_names_is_registered(scenario: GitScenarioSpec) -> None:
    """A typo in `assert:` is a check that never runs — one fewer constraint
    than the author wrote, with nothing to say so (PLAN.md §5.4).

    Asserted here as well as in the schema because this is the rule most likely
    to be loosened by accident: the schema check is one `if` in a validator, and
    a refactor that dropped it would leave the shipped library still loading.
    """
    unregistered = sorted(
        check.assertion
        for check in scenario.checks
        if not registry.is_registered(check.assertion)
    )

    assert unregistered == []


def test_it_has_at_least_one_required_check(scenario: GitScenarioSpec) -> None:
    """An exercise whose checks are all advisory passes vacuously, which is
    worse than having no exercise at all (PLAN.md §5.4).
    """
    assert scenario.required_checks


def test_every_check_a_human_has_to_read_says_something(
    scenario: GitScenarioSpec,
) -> None:
    """The `label` is the sentence in the verdict panel. A check that reports
    `tree_equals: false` and nothing else has graded you without teaching you,
    which is the failure §1 exists to reject.
    """
    assert all(check.label.strip() for check in scenario.checks)


def test_every_required_check_explains_itself(scenario: GitScenarioSpec) -> None:
    """An advisory can stand on its label; a *required* check that fails is the
    moment the learner most needs the why, so it has to carry an explanation.

    Deliberately not a domain invariant and deliberately not in the schema: an
    exercise missing an explanation is representable, and someone may be halfway
    through drafting it. It is still not shippable (PLAN.md §4.2, §9). This rule
    found a real gap the day it was written — `recover-a-lost-commit`'s
    `clean-worktree` had shipped with a label and nothing else.
    """
    missing = sorted(
        check.id
        for check in scenario.required_checks
        if not (check.explanation or "").strip()
    )

    assert missing == []


def test_it_ships_a_counter_example(scenario: GitScenarioSpec) -> None:
    """The mitigation for the highest-likelihood risk in PLAN.md §13:
    assertions too loose to tell right from wrong. A check that passes for both
    the correct answer and the naive one is worse than no check because it
    reports green, and only a counter-example can catch that.
    """
    assert scenario.counter_examples


def test_every_counter_example_names_a_check_that_exists(
    scenario: GitScenarioSpec,
) -> None:
    """ "Fails at least one check" is too weak a contract: a counter-example that
    refers to a reflog index depends on a position that shifts when a command is
    added, so an edit could leave it failing for an unrelated reason — or passing
    outright — with CI none the wiser (PLAN.md §5.4).
    """
    for example in scenario.counter_examples:
        assert example.expect_failures <= scenario.check_ids


def test_it_allows_git(scenario: GitScenarioSpec) -> None:
    """A git scenario the solver cannot run git in is not one."""
    assert "git" in scenario.allowed_commands


def test_every_reference_command_is_one_the_solver_could_type(
    scenario: GitScenarioSpec, scenario_directory: Path
) -> None:
    """The PLAN.md §5.3 guarantee, per exercise.

    If reference solutions were validated through an execution path the solver
    cannot use, CI would prove only that *a* solution exists, not that one
    exists within the rules — and a scenario could ship literally unsolvable
    with the build still green.
    """
    for name in scenario.command_lists:
        text = (scenario_directory / name).read_text(encoding="utf-8")
        for command in parse_command_list(text):
            assert command.program in scenario.allowed_commands, (
                f"{name}:{command.lineno}"
            )


def test_no_reference_command_uses_alias_syntax(
    scenario: GitScenarioSpec, scenario_directory: Path
) -> None:
    """`@c2` is assertion syntax only.

    A content author reaches for it in `solution.cmds` because they have just
    written five checks that use it, and it cannot work there: an alias is
    resolved from the fixture's map before git sees it in a *check*, while the
    solver only ever sees real revisions. Found by authoring the flagship
    scenario (§6.6), and the kind of mistake that would sit in a file for months
    before anyone ran it.
    """
    for name in scenario.command_lists:
        text = (scenario_directory / name).read_text(encoding="utf-8")
        for command in parse_command_list(text):
            offenders = [word for word in command.argv if word.startswith("@")]
            assert offenders == [], f"{name}:{command.lineno} uses {offenders}"


# --- katas -----------------------------------------------------------------


def test_a_kata_declares_the_complexity_it_expects(kata: KataSpec) -> None:
    """Never auto-graded — static Big-O analysis of arbitrary code is not
    something to pretend to do — but it is what the solver's own claim is
    reconciled against, and a kata without one has nothing to disagree with
    (PLAN.md §7).
    """
    assert kata.complexity is not None


def test_a_katas_stub_and_reference_are_different_files(kata: KataSpec) -> None:
    """A reference that *is* the stub would pass the Phase 4 oracle by being the
    same file twice, which is exactly what that oracle exists to catch.
    """
    assert kata.stub != kata.reference


# --- the repository sees what the walk sees --------------------------------


def test_the_repository_loads_the_whole_library() -> None:
    """`FilesystemContentRepository` and the validation walk must agree about
    what is in the library. They share `discover`, and this is the test that
    notices if one of them ever stops.

    Compared as sets, because the listing is in curriculum order since Phase 11
    and the walk is in filesystem order. What the two have to agree about is
    *membership* — `test_the_curriculum_orders_the_whole_library` is what holds
    the order to the manifest.
    """
    repository = FilesystemContentRepository(CONTENT_ROOT)

    assert {str(exercise.id) for exercise in repository.list_exercises()} == {
        _identify(directory) for directory in EXERCISE_DIRECTORIES
    }


def test_the_first_screen_of_the_curriculum_offers_every_kind() -> None:
    """The dashboard offers the top `QUEUE_LIMIT` rows, so the curriculum's first
    few entries *are* the product's front page on a fresh install.

    A content rule rather than a web one, and it exists because the first draft
    of the manifest broke it: a leading track of six git exercises filled all six
    rows and pushed every kata off the first screen. Interleaving at track
    granularity does not interleave the first thing anybody sees.
    `tests/e2e/test_schedule_a_review.py` is what noticed — it asks for Two Sum
    on the dashboard — and it took the whole suite to find, so the claim is
    asserted here where `-m content` can check it in milliseconds.

    **Asserted against the enum rather than against a literal pair as of Phase
    14.** It used to read `tracks == {"git", "katas"}`, and a third kind made
    that a statement about which two kinds existed when it was written. Deriving
    the expectation from `ExerciseKind` means a fourth kind fails here — on the
    first screen having no room for it, which is the decision that should be
    forced rather than discovered.

    It is also now tight: `QUEUE_LIMIT` is six and `start-here` is exactly six
    long, two of each kind. There is no slack left, which is the point of
    stating it.
    """
    curriculum = load_curriculum(CONTENT_ROOT)
    repository = FilesystemContentRepository(CONTENT_ROOT)
    by_id = {exercise.id: exercise for exercise in repository.list_exercises()}

    first_screen = curriculum.exercise_ids[:QUEUE_LIMIT]
    kinds = {by_id[exercise_id].kind for exercise_id in first_screen}

    assert kinds == set(ExerciseKind), sorted(str(one) for one in first_screen)


def test_the_curriculum_orders_the_whole_library() -> None:
    """The listing is the manifest, in the manifest's order.

    Stated as an equality of *lists* so it fails on a reordering as well as on a
    missing exercise — `validate_library` already refuses a manifest that omits
    one, and this is the half that proves the order is actually used rather than
    merely declared.
    """
    repository = FilesystemContentRepository(CONTENT_ROOT)
    curriculum = load_curriculum(CONTENT_ROOT)

    assert [exercise.id for exercise in repository.list_exercises()] == list(
        curriculum.exercise_ids
    )


# --- the tripwire ----------------------------------------------------------


def test_the_unproven_guarantees_are_still_unproven() -> None:
    """Fails when the check engine lands, which is the point.

    PLAN.md §11 says not to mistake green here for content that works, and a
    note in a plan is not a mechanism. When `unproven_by_design` shrinks,
    someone has to come back and write the grading tests rather than leaving a
    known gap covered by a comment nobody reads.

    Phase 3 narrowed the first of the three rather than removing it: fixtures
    and reference replays are now exercised for real by
    `tests/content/test_fixtures.py`, and what remains unproven is whether a
    replayed solution's end state actually *passes* its checks.

    Phase 4 removed the third — `tests/content/test_katas.py` grades every
    kata's reference and its stub — which is the tripwire doing its job: the
    count below had to be lowered by hand, by someone who had just written the
    tests that earned it. What is left is scenario grading, in Phase 5.
    """
    assert len(unproven_by_design()) == 2, (
        "a guarantee changed: write the grading tests PLAN.md §9 describes, "
        "then update this count"
    )
