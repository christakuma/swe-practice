"""The object graph the application tests drive, built out of fakes.

One builder rather than a fixture per port, because every test here needs the
same six and wants to reach into two or three of them afterwards — `world.attempts`
to assert what was saved, `world.provisioner` to assert what was built. A
`Services`-shaped bundle gets both without eight fixture parameters per test.

Deliberately *not* `practice.composition.Services`: that one builds the real
adapters, and a unit test that reached for it would provision real directories.
What this shares with it is the shape, which is the thing worth sharing — a test
that wires the ports the same way the composition root does is a test that would
notice the root wiring them differently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from practice.adapters.persistence import InMemoryAttemptRepository
from practice.application.registry import GraderRegistry
from practice.application.use_cases import (
    RunScenarioCommand,
    StartAttempt,
    SubmitScenario,
    SubmitSolution,
)
from practice.domain.attempt import SolutionSaved
from practice.domain.exercise import ExerciseKind
from practice.domain.verdict import CheckReport, Severity, Verdict
from tests.fakes import (
    FakeClock,
    FakeContentRepository,
    FakeProvisioner,
    SequentialIdGenerator,
    a_kata,
    a_scenario,
)

if TYPE_CHECKING:
    from practice.domain.attempt import Attempt
    from practice.domain.exercise import ComplexityExpectation, Exercise
    from practice.domain.ids import AttemptId
    from practice.domain.ports import Grader, Workspace

__all__ = [
    "ExplodingGrader",
    "FailingProvisioner",
    "NullGrader",
    "RecordingGrader",
    "World",
    "a_passing_verdict",
    "a_run_scenario_command",
    "a_start_attempt",
    "a_submit_scenario",
    "a_submit_solution",
    "an_environment",
]


class NullGrader:
    """Satisfies `Grader` and is never expected to be called."""

    def grade(
        self, exercise: Exercise, workspace: Workspace, attempt: Attempt
    ) -> Verdict:
        del exercise, workspace, attempt
        raise AssertionError("this grader should not have been reached")


class RecordingGrader:
    """Satisfies `Grader`, returns a canned verdict, remembers its arguments.

    It records the attempt's *state at the time it was called* rather than the
    attempt itself, because the aggregate keeps mutating afterwards — a test
    asserting "the source was saved before grading" has to look at what was true
    during the call, not at the end.
    """

    def __init__(self, verdict: Verdict | None = None) -> None:
        self._verdict = verdict if verdict is not None else a_passing_verdict()
        self.calls: list[tuple[str, int, bool]] = []

    def grade(
        self, exercise: Exercise, workspace: Workspace, attempt: Attempt
    ) -> Verdict:
        del exercise
        self.calls.append(
            (
                _latest_source(attempt),
                len(attempt.events),
                getattr(workspace, "disposed", False),
            )
        )
        return self._verdict


class ExplodingGrader:
    """Satisfies `Grader` and raises. A class rather than a monkeypatched method
    so the type checker still sees a `Grader` where one is required.
    """

    def grade(
        self, exercise: Exercise, workspace: Workspace, attempt: Attempt
    ) -> Verdict:
        del exercise, workspace, attempt
        raise RuntimeError("grader exploded")


class FailingProvisioner:
    """A provisioner whose fixture blows up, for the half-built cases."""

    def provision(self, exercise: Exercise, attempt_id: AttemptId) -> Workspace:
        del exercise, attempt_id
        raise RuntimeError("fixture exploded")

    def attach(
        self, exercise: Exercise, attempt_id: AttemptId
    ) -> Workspace | None:  # pragma: no cover - never reached in these tests
        del exercise, attempt_id
        return None


def a_passing_verdict() -> Verdict:
    return Verdict(
        reports=(
            CheckReport(
                check_id="finds-the-pair",
                label="Finds the two positions that add up to the target.",
                severity=Severity.REQUIRED,
                passed=True,
            ),
        )
    )


def a_failing_verdict() -> Verdict:
    return Verdict(
        reports=(
            CheckReport(
                check_id="finds-the-pair",
                label="Finds the two positions that add up to the target.",
                severity=Severity.REQUIRED,
                passed=False,
            ),
        )
    )


@dataclass
class World:
    """Every port a use case needs, and nothing a use case does not."""

    content: FakeContentRepository
    attempts: InMemoryAttemptRepository
    provisioner: FakeProvisioner
    graders: GraderRegistry
    clock: FakeClock
    ids: SequentialIdGenerator
    grader: Grader = field(default_factory=RecordingGrader)
    scenario_grader: Grader = field(default_factory=RecordingGrader)

    @property
    def scenario_recorder(self) -> RecordingGrader:
        """The scenario grader as the recording one. See `recorder`."""
        assert isinstance(self.scenario_grader, RecordingGrader)
        return self.scenario_grader

    @property
    def recorder(self) -> RecordingGrader:
        """The kata grader as the recording one, for the tests that assert on it.

        Narrowed here rather than at every call site: `grader` is typed as the
        port because a test may substitute `ExplodingGrader`, and a test that
        reaches for `.calls` has already chosen the recording one.
        """
        assert isinstance(self.grader, RecordingGrader)
        return self.grader


def an_environment(
    *,
    complexity: ComplexityExpectation | None = None,
    grader: Grader | None = None,
    scenario_grader: Grader | None = None,
) -> World:
    """A world holding the two shipped exercise kinds and a grader for each.

    Both are registered, matching what the composition root does as of Phase 5. A
    test that wants a *missing* grader builds the registry it wants and passes it to
    the use-case builder, which is the honest way to express that -- a shared
    environment quietly short of one grader would make every test in the file depend
    on which half was missing.
    """
    kata_grader = grader if grader is not None else RecordingGrader()
    git_grader = scenario_grader if scenario_grader is not None else RecordingGrader()
    return World(
        content=FakeContentRepository(
            [a_kata(complexity=complexity), a_scenario()],
        ),
        attempts=InMemoryAttemptRepository(),
        provisioner=FakeProvisioner(),
        graders=GraderRegistry(
            graders={
                ExerciseKind.KATA: kata_grader,
                ExerciseKind.GIT_SCENARIO: git_grader,
            }
        ),
        clock=FakeClock(),
        ids=SequentialIdGenerator(start=0),
        grader=kata_grader,
        scenario_grader=git_grader,
    )


def a_start_attempt(
    world: World, *, graders: GraderRegistry | None = None
) -> StartAttempt:
    return StartAttempt(
        content=world.content,
        attempts=world.attempts,
        provisioner=world.provisioner,
        graders=graders if graders is not None else world.graders,
        clock=world.clock,
        ids=world.ids,
    )


def a_submit_solution(world: World) -> SubmitSolution:
    return SubmitSolution(
        content=world.content,
        attempts=world.attempts,
        provisioner=world.provisioner,
        graders=world.graders,
        clock=world.clock,
    )


def a_run_scenario_command(world: World) -> RunScenarioCommand:
    """No grader registry: running a command does not grade anything."""
    return RunScenarioCommand(
        content=world.content,
        attempts=world.attempts,
        provisioner=world.provisioner,
        clock=world.clock,
    )


def a_submit_scenario(
    world: World, *, graders: GraderRegistry | None = None
) -> SubmitScenario:
    return SubmitScenario(
        content=world.content,
        attempts=world.attempts,
        provisioner=world.provisioner,
        graders=graders if graders is not None else world.graders,
        clock=world.clock,
    )


def _latest_source(attempt: Attempt) -> str:
    saved = [event for event in attempt.events if isinstance(event, SolutionSaved)]
    return saved[-1].source if saved else ""
