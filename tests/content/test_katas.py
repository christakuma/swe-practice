"""Every kata on disk, actually solved — and actually failed.

The half of PLAN.md §9's content suite that Phase 4 lands: *"katas:
`solution.py` **passes** and `stub.py` **fails** (a test suite that passes an
empty stub is a broken test suite)"*. Both halves matter and the second is the
one people leave out. A suite that passes the stub is not a weak suite, it is a
suite that grades nothing, and it would make its exercise report success for
every solution ever submitted to it.

Parametrized over the real `content/` directory, so adding a kata adds test
cases without touching this file — the content-as-data bet applied to its own
tests. It is the slowest file in the project per exercise: two pytest
subprocesses per kata. That is the price of proving content works, and §11 is
explicit that structural validation is not the same claim.

**What this cannot prove, and does not pretend to.** That the suite is
*discriminating* — that it would reject a plausible wrong answer rather than
only an unimplemented one. `tests/integration/kata/test_pytest_runner.py` holds
one such case for two-sum by hand; the general form would need a counter-example
per kata, which is what git scenarios already require (§5.4) and what katas
should grow if the library gets large enough to need it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.content import ContentError, load_exercise
from practice.adapters.content.validation import discover
from practice.adapters.kata import KataGrader, PytestKataRunner
from practice.adapters.sandbox import SubprocessSandboxProvisioner, find_git
from practice.config import content_root
from practice.domain.attempt import Attempt, AttemptPolicy, ComplexityClaim
from practice.domain.exercise import KataSpec
from practice.domain.ids import AttemptId
from practice.domain.verdict import Outcome
from tests.fakes import FakeClock

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from practice.adapters.sandbox import SubprocessWorkspace
    from practice.domain.exercise import Exercise
    from practice.domain.verdict import Verdict

CONTENT_ROOT = content_root()


def _identify(directory: Path) -> str:
    return directory.relative_to(CONTENT_ROOT).as_posix()


def _kata_directories() -> list[Path]:
    """Every kata directory, found defensively.

    A directory that will not load belongs to no kind and is reported by the
    `validate` suite instead, rather than crashing collection here.
    """
    found = []
    for directory in sorted(discover(CONTENT_ROOT)):
        try:
            exercise = load_exercise(directory)
        except ContentError:
            continue
        if isinstance(exercise.spec, KataSpec):
            found.append(directory)
    return found


KATA_DIRECTORIES = _kata_directories()

type Grade = Callable[[str, ComplexityClaim | None], Verdict]


@pytest.fixture(scope="session")
def git() -> Path:
    """Resolve git once, failing loudly rather than skipping.

    A content suite that silently skips when a tool is missing reports success
    exactly as loudly as one that ran every kata (PLAN.md §9).
    """
    return find_git()


@pytest.fixture(params=KATA_DIRECTORIES, ids=_identify)
def kata_directory(request: pytest.FixtureRequest) -> Path:
    directory: Path = request.param
    return directory


@pytest.fixture
def exercise(kata_directory: Path) -> Exercise:
    return load_exercise(kata_directory)


@pytest.fixture
def spec(exercise: Exercise) -> KataSpec:
    assert isinstance(exercise.spec, KataSpec)
    return exercise.spec


@pytest.fixture
def grade(git: Path, tmp_path: Path, exercise: Exercise) -> Iterator[Grade]:
    """Grade a source against this kata, in a workspace of its own each time.

    A factory rather than one workspace, because grading writes `solution.py`
    and a report into it: a second grading in the same directory would start
    from the first one's leftovers, and what it proved would depend on the order
    the tests happen to be declared in.
    """
    del git  # requested so a missing tool fails here, not mid-fixture
    provisioner = SubprocessSandboxProvisioner(
        content_root=CONTENT_ROOT, workspace_root=tmp_path / "ws"
    )
    grader = KataGrader(PytestKataRunner())
    provisioned: list[SubprocessWorkspace] = []

    def run(source: str, claim: ComplexityClaim | None = None) -> Verdict:
        attempt_id = AttemptId.parse(
            f"{len(provisioned):08x}-0000-4000-8000-000000000000"
        )
        workspace = provisioner.provision(exercise, attempt_id)
        provisioned.append(workspace)

        clock = FakeClock()
        attempt = Attempt(
            attempt_id=attempt_id,
            exercise_id=exercise.id,
            policy=AttemptPolicy.for_exercise(exercise),
            started_at=clock.now(),
        )
        attempt.save_solution(source, at=clock.now())
        if claim is not None:
            attempt.declare_complexity(claim)
        return grader.grade(exercise, workspace, attempt)

    try:
        yield run
    finally:
        for workspace in provisioned:
            workspace.dispose()


def _read(directory: Path, name: str) -> str:
    return (directory / name).read_text(encoding="utf-8")


# --- the walk --------------------------------------------------------------


def test_there_are_katas_to_grade() -> None:
    """Without this, every parametrized test below is vacuously true."""
    assert KATA_DIRECTORIES


# --- every kata ------------------------------------------------------------


def test_its_reference_solution_passes_every_check(
    grade: Grade, spec: KataSpec, kata_directory: Path
) -> None:
    """The guarantee `practice validate` admitted it could not make until now.

    The complexity expectation, where there is one, is declared to match — so a
    failure here is about the solution and the suite rather than about an
    advisory the reference was never going to satisfy.
    """
    claim = (
        ComplexityClaim(
            time=spec.complexity.expected_time, space=spec.complexity.expected_space
        )
        if spec.complexity is not None
        else None
    )

    verdict = grade(_read(kata_directory, spec.reference), claim)

    assert verdict.outcome is Outcome.PASS, "\n".join(
        f"{report.check_id}: {report.actual} -- {report.explanation}"
        for report in verdict.reports
        if not report.passed
    )


def test_its_stub_fails(grade: Grade, spec: KataSpec, kata_directory: Path) -> None:
    """A suite that passes an unimplemented stub grades nothing at all.

    Only that the verdict *fails* is asserted, not that every single check does:
    a stub that happens to satisfy a trivial case — an empty-input test, say — is
    a legitimate kata, while one that satisfies all of them is a broken one.
    """
    verdict = grade(_read(kata_directory, spec.stub), None)

    assert verdict.outcome is Outcome.FAIL


def test_its_hidden_suite_holds_more_than_one_test(
    grade: Grade, spec: KataSpec, kata_directory: Path
) -> None:
    """One check is not a kata.

    Reusing the reference run would be faster, but a check *count* taken from a
    passing run cannot distinguish a one-test suite from a one-test suite that
    passed — which is the thing being ruled out. The stub run is the cheap one
    to count, since the complexity advisory is excluded by severity.
    """
    verdict = grade(_read(kata_directory, spec.stub), None)
    required = [report for report in verdict.reports if report.is_required]

    assert len(required) > 1, [report.check_id for report in required]


def test_its_declared_complexity_is_compared_rather_than_graded(
    grade: Grade, spec: KataSpec, kata_directory: Path
) -> None:
    """A deliberately absurd claim must never fail the attempt.

    Static Big-O analysis of arbitrary code is not something this tool pretends
    to do (PLAN.md §7), so a disagreement is an advisory to reconcile.

    Both branches assert something, which is why there is no `pytest.skip` here:
    a kata that states an expectation gets exactly one advisory, and a kata that
    states none gets no complexity check at all — inventing one would fail every
    attempt at an exercise whose author was simply quieter.
    """
    verdict = grade(
        _read(kata_directory, spec.reference),
        ComplexityClaim(time="O(n!)", space="O(n!)"),
    )

    assert verdict.passed, "a complexity claim must never fail an attempt"
    if spec.complexity is None:
        assert verdict.outcome is Outcome.PASS
        assert verdict.advisories == ()
    else:
        assert verdict.outcome is Outcome.PASS_WITH_ADVISORIES
        assert len(verdict.advisories) == 1
