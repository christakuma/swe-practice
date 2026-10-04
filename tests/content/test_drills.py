"""Every SQL drill on disk, actually solved — and actually failed.

The drill half of PLAN.md §9's content suite, and the standard is the one Phase
11 set for git scenarios rather than the lighter one katas get: **every drill's
reference solution is graded through the real use case, and every
counter-example is required to fail exactly the checks it declares.**

`tests/content/test_katas.py` says why that stronger standard matters and that
katas do not yet meet it — "a counter-example per kata, which is what git
scenarios already require (§5.4) and what katas should grow". Drills are
authored to it from the first one, because a declarative check vocabulary makes
it cheap: a counter-example is one `.sql` file and a list of check ids.

**This file is fast**, which is the thing that makes the standard affordable
here. A drill is seeded in `:memory:` and graded in under a millisecond, where a
kata costs two pytest subprocesses and a git scenario costs a bash fixture and a
dozen `git` calls. The whole file runs in about the time one kata takes.

The verdict per file is memoised, because `expect_failures` is checked one
check at a time and re-grading the same answer per assertion would be the one
thing here that could get slow.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.content import ContentError, load_exercise
from practice.adapters.content.validation import discover
from practice.adapters.sql import ANSWER_CHECK_ID, SqlDrillGrader
from practice.config import content_root
from practice.domain.attempt import Attempt, AttemptPolicy
from practice.domain.drills import registry as drills
from practice.domain.exercise import SqlDrillSpec
from practice.domain.ids import AttemptId
from practice.domain.verdict import Outcome, Severity
from tests.fakes import FakeClock, FakeWorkspace

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.exercise import Exercise
    from practice.domain.verdict import Verdict

CONTENT_ROOT = content_root()


def _drill_directories() -> list[Path]:
    """Every SQL drill directory, found defensively.

    A directory that will not load belongs to no kind and is reported by the
    `validate` suite instead, rather than crashing collection here — the same
    rule `tests/content/conftest.py` states for scenarios.
    """
    found = []
    for directory in sorted(discover(CONTENT_ROOT)):
        try:
            exercise = load_exercise(directory)
        except ContentError:
            continue
        if isinstance(exercise.spec, SqlDrillSpec):
            found.append(directory)
    return found


DRILLS = _drill_directories()
IDS = [directory.relative_to(CONTENT_ROOT).as_posix() for directory in DRILLS]

#: `(directory, answer filename) -> Verdict`. Module-scoped by being module
#: level, which is why `--dist loadfile` matters: every test in this file lands
#: on one xdist worker and shares it.
_VERDICTS: dict[tuple[Path, str], Verdict] = {}


def grade(directory: Path, filename: str) -> Verdict:
    """Grade one answer file against its drill, through the real grader."""
    key = (directory, filename)
    if key not in _VERDICTS:
        exercise = load_exercise(directory)
        spec = exercise.spec
        assert isinstance(spec, SqlDrillSpec)
        clock = FakeClock()
        attempt = Attempt(
            attempt_id=AttemptId.parse("aabbccdd-0000-4000-8000-000000000001"),
            exercise_id=exercise.id,
            policy=AttemptPolicy.for_exercise(exercise),
            started_at=clock.now(),
        )
        attempt.save_solution(
            (directory / filename).read_text(encoding="utf-8"), at=clock.now()
        )
        workspace = FakeWorkspace(
            files={spec.seed: (directory / spec.seed).read_text(encoding="utf-8")}
        )
        _VERDICTS[key] = SqlDrillGrader().grade(exercise, workspace, attempt)
    return _VERDICTS[key]


def _describe(verdict: Verdict) -> str:
    """Every failing report, as the message a content failure should carry.

    A content test that fails with `assert verdict.passed` tells you which
    exercise and nothing else, and the next step is always to go and run the
    reference by hand. This puts the check id, what it wanted and what it found
    into the failure itself -- which is the same argument `CheckReport` makes for
    carrying `expected` and `actual` at all.
    """
    lines = [
        f"  {report.check_id}: expected {report.expected!r}, got {report.actual!r}"
        for report in verdict.reports
        if not report.passed
    ]
    return "\n".join(["", *lines]) if lines else " (nothing failed)"


def spec_of(directory: Path) -> SqlDrillSpec:
    spec = load_exercise(directory).spec
    assert isinstance(spec, SqlDrillSpec)
    return spec


def exercise_of(directory: Path) -> Exercise:
    return load_exercise(directory)


# --- the references --------------------------------------------------------


@pytest.mark.parametrize("directory", DRILLS, ids=IDS)
def test_the_reference_solution_passes(directory: Path) -> None:
    """The claim `practice validate` explicitly cannot make.

    Structural validation proves the file loads and names real assertions. This
    proves the reference reaches the end state those assertions describe — which
    is the only thing that makes the exercise solvable.
    """
    verdict = grade(directory, spec_of(directory).reference)

    assert verdict.passed, _describe(verdict)


@pytest.mark.parametrize("directory", DRILLS, ids=IDS)
def test_the_reference_solution_runs_cleanly(directory: Path) -> None:
    """Separate from passing, because `answer-ran` is a synthesised check and a
    reference that produced a SQLite error could in principle still satisfy
    every *declared* check about an unchanged database.
    """
    verdict = grade(directory, spec_of(directory).reference)
    [answer] = [r for r in verdict.reports if r.check_id == ANSWER_CHECK_ID]

    assert answer.passed, answer.actual


@pytest.mark.parametrize("directory", DRILLS, ids=IDS)
def test_the_reference_triggers_no_advisories(directory: Path) -> None:
    """A reference is the *best* answer, not merely a correct one.

    A drill whose own reference trips its own advisory is a drill telling the
    solver to do something it does not do itself — and `use-the-index-you-were
    -given` is exactly the exercise where that would be embarrassing.
    """
    verdict = grade(directory, spec_of(directory).reference)

    assert verdict.outcome is Outcome.PASS, _describe(verdict)


@pytest.mark.parametrize("directory", DRILLS, ids=IDS)
def test_the_stub_does_not_pass(directory: Path) -> None:
    """A drill whose stub passes is a drill that grades nothing.

    The kata suite's "`stub.py` must fail" rule, for drills. A stub is comments
    only, so it submits no statements at all — and a check vocabulary that
    passed an empty answer would pass every answer.
    """
    verdict = grade(directory, spec_of(directory).stub)

    assert not verdict.passed, _describe(verdict)


# --- the counter-examples --------------------------------------------------


def _counter_cases() -> list[tuple[Path, str, str]]:
    """`(directory, counter-example file, check id)`, one case per expectation.

    Flattened to one case per *check* rather than per file, so a failure names
    the exact check that stopped failing rather than a set difference.
    """
    cases = []
    for directory in DRILLS:
        for example in spec_of(directory).counter_examples:
            for check_id in sorted(example.expect_failures):
                cases.append((directory, example.file, check_id))
    return cases


COUNTER_CASES = _counter_cases()
COUNTER_IDS = [
    f"{directory.relative_to(CONTENT_ROOT).as_posix()}::{filename}::{check_id}"
    for directory, filename, check_id in COUNTER_CASES
]


@pytest.mark.parametrize(
    ("directory", "filename", "check_id"), COUNTER_CASES, ids=COUNTER_IDS
)
def test_a_counter_example_fails_the_check_it_declares(
    directory: Path, filename: str, check_id: str
) -> None:
    """§5.4's contract: "fails at least one check" is too weak.

    A counter-example that stops failing the check it was written for — because
    the data changed, or the check was retuned — is a counter-example that
    proves nothing while still being green. Naming the expected failure turns
    that rot into a build failure.
    """
    verdict = grade(directory, filename)
    [report] = [r for r in verdict.reports if r.check_id == check_id]

    assert not report.passed, (
        f"{filename} was expected to fail {check_id}, and it passed: "
        f"expected {report.expected!r}, got {report.actual!r}"
    )


@pytest.mark.parametrize("directory", DRILLS, ids=IDS)
def test_a_counter_example_fails_nothing_it_does_not_declare(
    directory: Path,
) -> None:
    """The other half, and the one that keeps the list honest.

    Without it, `expect_failures` would be a lower bound and a counter-example
    could quietly start failing a check for an unrelated reason — which is how a
    counter-example comes to be evidence about something other than what it was
    written for.
    """
    spec = spec_of(directory)
    for example in spec.counter_examples:
        verdict = grade(directory, example.file)
        failed = {r.check_id for r in verdict.reports if not r.passed}
        failed.discard(ANSWER_CHECK_ID)

        assert failed == set(example.expect_failures), (
            f"{example.file} declares it fails {sorted(example.expect_failures)} "
            f"and actually fails {sorted(failed)}"
        )


@pytest.mark.parametrize("directory", DRILLS, ids=IDS)
def test_every_counter_example_runs_cleanly(directory: Path) -> None:
    """**A counter-example must be a plausible wrong answer, not a broken one.**

    The failure this prevents is the most insidious available in a drill: a
    counter-example with a typo in it fails every check, so every
    `expect_failures` entry is satisfied and the file proves nothing about the
    mistake it was written to demonstrate. Requiring it to *run* is what makes
    it evidence — a wrong answer SQLite accepted.

    Not required of the stub, which is comments and is meant to submit nothing.
    """
    spec = spec_of(directory)
    for example in spec.counter_examples:
        verdict = grade(directory, example.file)
        [answer] = [r for r in verdict.reports if r.check_id == ANSWER_CHECK_ID]

        assert answer.passed, f"{example.file} did not run: {answer.actual}"


@pytest.mark.parametrize("directory", DRILLS, ids=IDS)
def test_every_drill_has_a_counter_example(directory: Path) -> None:
    """The standard drills are authored to, stated so it cannot slip.

    `GitScenarioSpec` does not require one and neither does `SqlDrillSpec` — a
    drill somebody is halfway through drafting is representable. Shipping one is
    different, and this is the line between the two.
    """
    assert spec_of(directory).counter_examples, (
        "a drill with no counter-example has only been shown to accept a right "
        "answer, not to reject a wrong one"
    )


# --- the library as a whole ------------------------------------------------


def test_there_are_eight_drills() -> None:
    """A literal count, so a ninth is a deliberate edit rather than a surprise."""
    assert len(DRILLS) == 8


def test_every_drill_assertion_is_used_by_some_drill() -> None:
    """**§13's rule, enforced rather than quoted.**

    Phase 11 deleted `reflog_contains` and `command_count` from the git
    vocabulary because 24 scenarios wanted neither. The same standard applies
    to all ten drill assertions, and this is what applies it: an eleventh
    should not be added before the exercise that wants it exists, and one that
    stops being used should go.
    """
    used = {
        check.assertion for directory in DRILLS for check in spec_of(directory).checks
    }

    assert used == drills.DRILL_ASSERTIONS, (
        f"unused: {sorted(drills.DRILL_ASSERTIONS - used)}"
    )


def test_every_drill_grades_the_database_or_the_answer() -> None:
    """Every drill has a required check that reads state, not just craft.

    `validate` enforces this too (`_audit_something_is_graded`), and it is worth
    a second statement here because the two are different claims: that one is
    about any library, this one is about the library that ships.
    """
    for directory in DRILLS:
        required = [c for c in spec_of(directory).checks if c.is_required]
        state = [c for c in required if c.assertion in drills.STATE_ASSERTIONS]

        assert state, f"{directory.name} requires no check that reads state"


@pytest.mark.parametrize("directory", DRILLS, ids=IDS)
def test_every_craft_check_is_advisory(directory: Path) -> None:
    """The convention `craft.py` states, held over the library.

    Nothing in the domain enforces it — `CRAFT_ASSERTIONS` exists so that this
    test can, which is the same arrangement `command_used` has on the git side.
    A *required* check over the text of an answer is the string matching
    ADR 0003 rejected.
    """
    for check in spec_of(directory).checks:
        if check.assertion in drills.CRAFT_ASSERTIONS:
            assert check.severity is Severity.ADVISORY, (
                f"{check.id} grades craft and is required; §4.4 grades craft "
                f"separately from correctness"
            )


@pytest.mark.parametrize("directory", DRILLS, ids=IDS)
def test_the_seed_is_in_the_workspace_and_the_reference_is_not(
    directory: Path,
) -> None:
    """The split `_install_drill_files` makes, asserted against real content.

    The seed is copied in because the grader reads it there *and* because the
    solver is meant to read the schema. The reference is not, because it is an
    answer key.
    """
    spec = spec_of(directory)

    assert (directory / spec.seed).is_file()
    assert (directory / spec.reference).is_file()
    assert spec.seed in spec.referenced_files
    assert spec.reference in spec.referenced_files


@pytest.mark.parametrize("directory", DRILLS, ids=IDS)
def test_a_drill_is_described_well_enough_to_attempt(directory: Path) -> None:
    """Hints, notes, and a prompt that mentions the schema file.

    The last clause is a drill-specific rule: the schema is in the workspace on
    purpose, and a prompt that never says so leaves the solver guessing at
    column names they could have read.
    """
    exercise = exercise_of(directory)

    assert exercise.hints, "a drill with no hints has no way back for a stuck solver"
    assert exercise.notes.strip(), "the notes are where the why lives"
    assert len(exercise.hints) >= 2, "a single hint is either the answer or nothing"


def test_at_least_one_drill_is_graded_purely_on_the_end_state() -> None:
    """The claim that makes this an exercise *kind* rather than a query checker.

    A library of `SELECT` drills would be gradeable by comparing result sets
    alone, and `tables.py` would be dead weight. At least one drill has to
    return nothing and be graded entirely on what the database was left
    holding, or the core bet is not being exercised for this kind.
    """
    end_state_only = []
    for directory in DRILLS:
        checks = spec_of(directory).checks
        assertions = {check.assertion for check in checks if check.is_required}
        if assertions and assertions <= {"table_matches", "table_row_count"}:
            end_state_only.append(directory.name)

    assert end_state_only, "no drill is graded purely on the state it left behind"
