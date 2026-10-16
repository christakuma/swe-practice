"""The Run button's harness, run for real against shipped katas.

The half `RecordingExampleRunner` cannot stand in for: a subprocess under `-I`
importing a one-file solution, evaluating each example, and writing a report
the runner can read. ADR 0029.

**The parity tests are the ones worth keeping.** `examples_harness` restates the
content suite's comparison -- `repr` of the *plain* form, nodes walked by shape
-- in a file that cannot import that suite. If the two drift, a correct answer
shows as a mismatch on the page while the content suite is green, and nothing
else would notice. So a handful of katas whose answers are a tuple, a linked
list, a tree, a graph and a class are run through the harness with their own
reference, which the content suite already holds to every example.

**And the stale-report test is the lesson `pytest_runner._install` documents,
re-run**: a run killed at the time limit writes nothing, so a runner that
forgot to truncate would report the previous run's results as this one's.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from practice.adapters.kata import KataExampleRunner, PytestKataRunner
from practice.adapters.sandbox import SubprocessSandboxProvisioner
from practice.config import content_root
from practice.domain.exercise import KataSpec
from practice.domain.ids import AttemptId, ExerciseId

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from practice.adapters.content import FilesystemContentRepository
    from practice.adapters.sandbox import SubprocessWorkspace
    from practice.domain.exercise import Exercise

type Provision = Callable[[ExerciseId], tuple[Exercise, SubprocessWorkspace]]

#: One kata per shape of answer the comparison has a rule for.
PARITY = (
    "katas/two-sum",  # a tuple
    "katas/merge-two-sorted-lists",  # a linked list, walked by `next`
    "katas/invert-a-binary-tree",  # a tree, keeping its `None` children
    "katas/clone-a-graph",  # an expression over a returned object
    "katas/implement-a-trie",  # a class, constructed and asked
)

TWO_SUM = ExerciseId("katas/two-sum")
WRONG = "def two_sum(numbers, target):\n    return (1, 0)\n"
CHATTY = """\
def two_sum(numbers, target):
    print("looking at", numbers)
    return (0, 1)
"""
LOOPS_FOREVER = "def two_sum(numbers, target):\n    while True:\n        pass\n"
NOT_PYTHON = "this is not python at all\n"


@pytest.fixture
def runner() -> KataExampleRunner:
    return KataExampleRunner(PytestKataRunner())


@pytest.fixture
def provision(
    git: Path, tmp_path: Path, library: FilesystemContentRepository
) -> Iterator[Provision]:
    """A workspace for any kata in the library, disposed of afterwards."""
    del git  # requested so a missing tool fails here, not mid-test
    provisioner = SubprocessSandboxProvisioner(
        content_root=content_root(), workspace_root=tmp_path / "ws"
    )
    provisioned: list[SubprocessWorkspace] = []

    def build(exercise_id: ExerciseId) -> tuple[Exercise, SubprocessWorkspace]:
        exercise = library.get(exercise_id)
        assert exercise is not None, f"{exercise_id} is missing from the library"
        workspace = provisioner.provision(
            exercise,
            AttemptId.parse(f"{len(provisioned):08x}-0000-4000-8000-000000000000"),
        )
        provisioned.append(workspace)
        return exercise, workspace

    try:
        yield build
    finally:
        for workspace in provisioned:
            workspace.dispose()


def reference_of(exercise: Exercise) -> str:
    assert isinstance(exercise.spec, KataSpec)
    path = content_root() / exercise.id.value / exercise.spec.reference
    return path.read_text(encoding="utf-8")


def stub_of(exercise: Exercise) -> str:
    assert isinstance(exercise.spec, KataSpec)
    path = content_root() / exercise.id.value / exercise.spec.stub
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("slug", PARITY)
def test_a_reference_passes_every_example_through_the_harness(
    runner: KataExampleRunner, provision: Provision, slug: str
) -> None:
    exercise, workspace = provision(ExerciseId(slug))

    trial = runner.run(exercise, workspace, reference_of(exercise))

    assert trial.ran, trial.problem
    assert trial.all_passed, [
        (example.expected, example.actual, example.error) for example in trial.examples
    ]
    assert isinstance(exercise.spec, KataSpec)
    assert len(trial.examples) == len(exercise.spec.examples)


def test_the_stub_raises_on_every_example_and_says_what(
    runner: KataExampleRunner, provision: Provision
) -> None:
    exercise, workspace = provision(TWO_SUM)

    trial = runner.run(exercise, workspace, stub_of(exercise))

    assert trial.ran
    assert trial.passed == 0
    assert all(example.error == "NotImplementedError" for example in trial.examples)


def test_a_wrong_answer_shows_what_it_gave_beside_what_was_expected(
    runner: KataExampleRunner, provision: Provision
) -> None:
    exercise, workspace = provision(TWO_SUM)

    trial = runner.run(exercise, workspace, WRONG)

    first = trial.examples[0]
    assert not first.passed
    assert first.actual == "(1, 0)"
    assert first.expected == "(0, 1)"
    assert first.error is None


def test_what_an_example_prints_comes_back_with_it(
    runner: KataExampleRunner, provision: Provision
) -> None:
    exercise, workspace = provision(TWO_SUM)

    trial = runner.run(exercise, workspace, CHATTY)

    assert trial.examples[0].stdout.startswith("looking at [")


def test_a_source_that_does_not_import_is_a_problem_not_a_row_of_failures(
    runner: KataExampleRunner, provision: Provision
) -> None:
    exercise, workspace = provision(TWO_SUM)

    trial = runner.run(exercise, workspace, NOT_PYTHON)

    assert not trial.ran
    assert trial.examples == ()
    assert trial.problem is not None
    assert "could not be imported: SyntaxError" in trial.problem


def test_a_hung_example_is_reported_without_the_previous_runs_results(
    runner: KataExampleRunner, provision: Provision
) -> None:
    """In one workspace: a passing run first, so its report is on disk, then a
    run that is killed before it writes one."""
    exercise, workspace = provision(TWO_SUM)
    runner.run(exercise, workspace, reference_of(exercise))
    assert isinstance(exercise.spec, KataSpec)
    short = replace(exercise, spec=replace(exercise.spec, time_limit_seconds=2))

    trial = runner.run(short, workspace, LOOPS_FOREVER)

    assert not trial.ran
    assert trial.examples == ()
    assert trial.problem == "stopped after 2s: example 1 did not finish"


def test_a_run_leaves_the_solvers_own_file_alone(
    runner: KataExampleRunner, provision: Provision
) -> None:
    """Own-editor mode hands over the stub's file; Run writes `solution.py`, and
    the two must never be the same file."""
    exercise, workspace = provision(TWO_SUM)
    assert isinstance(exercise.spec, KataSpec)
    before = workspace.read_file(exercise.spec.stub)

    runner.run(exercise, workspace, WRONG)

    assert workspace.read_file(exercise.spec.stub) == before
