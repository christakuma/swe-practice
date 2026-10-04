"""`WatchSolutionFile`: a verdict per save, and a log that does not grow.

**The claim under test is a negative one**, which is why half of this file looks
at what did *not* happen: grade-on-save must leave the attempt exactly as it
found it (ADR 0013). A version that appended a `SolutionSaved` event per save
would pass every "the verdict is right" test here and quietly break the grade
suggestion, the process assertions in §6.3, and `latest_source`'s meaning.

The stream is an async generator, driven with `asyncio.run` and a scripted
watcher. No pytest-asyncio and no real filesystem event: the fake yields the
saves the test asked for, so what is being tested is what the use case does with
a save rather than how long it takes to notice one.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest

from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    UnsupportedExerciseKindError,
    WorkspaceGoneError,
)
from practice.domain.attempt import AttemptMode, SolutionSaved
from practice.domain.errors import AttemptStateError, PolicyViolationError
from practice.domain.ids import AttemptId, ExerciseId
from practice.domain.verdict import Outcome
from tests.unit.application.helpers import (
    RecordingGrader,
    a_failing_verdict,
    a_start_attempt,
    a_watch_solution_file,
    an_environment,
)

if TYPE_CHECKING:
    from practice.application.dto import Draft
    from tests.unit.application.helpers import World

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")

FIRST = "def two_sum(numbers, target):\n    return (0, 1)\n"
SECOND = "def two_sum(numbers, target):\n    return (1, 2)\n"

MISSING = AttemptId.parse("00000000-0000-4000-8000-000000000000")


def drain(world: World, attempt_id: AttemptId) -> list[Draft | None]:
    """Everything the stream yields, in order, until its script runs out."""

    async def collect() -> list[Draft | None]:
        return [draft async for draft in a_watch_solution_file(world)(attempt_id)]

    return asyncio.run(collect())


def test_a_save_produces_a_verdict_for_what_is_in_the_file() -> None:
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.provisioner.workspace_for(started.attempt.id).write_file("stub.py", FIRST)
    world.watcher.saves()

    drafts = drain(world, started.attempt.id)

    assert [draft.source for draft in drafts if draft] == [FIRST]
    assert world.recorder.calls == [(FIRST, 1, False)]


def test_every_save_is_graded_against_what_the_file_then_held() -> None:
    """Two saves, two verdicts, and the second one is about the second source.

    The file is read at grading time rather than carried from the first pass,
    which is the whole premise: the file is the solution.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    workspace = world.provisioner.workspace_for(started.attempt.id)
    workspace.write_file("stub.py", FIRST)
    world.watcher.saves()

    async def collect() -> list[str]:
        seen: list[str] = []
        async for draft in a_watch_solution_file(world)(started.attempt.id):
            if draft is None:
                continue
            seen.append(draft.source)
            if len(seen) == 1:
                # Scripted from inside the loop, after the first pass has been
                # graded: the fake's script is a queue, so this is the order a
                # solver produces rather than two saves arranged up front. Only
                # once -- appending on every draft is a stream with no end.
                workspace.write_file("stub.py", SECOND)
                world.watcher.saves()
        return seen

    assert asyncio.run(collect()) == [FIRST, SECOND]


def test_the_attempts_event_log_is_untouched() -> None:
    """ADR 0013, as a test. An editor save is a keystroke, not something the
    solver did in the exercise -- so nothing is persisted, however many times
    they press Ctrl+S.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.provisioner.workspace_for(started.attempt.id).write_file("stub.py", FIRST)
    before = len(started.attempt.events)
    world.watcher.saves(3)

    drain(world, started.attempt.id)

    stored = world.attempts.get(started.attempt.id)
    assert stored is not None
    assert len(stored.events) == before
    assert not [event for event in stored.events if isinstance(event, SolutionSaved)]


def test_the_attempt_is_not_completed_by_being_graded() -> None:
    """The reason this is a use case of its own rather than `SubmitSolution` on
    a timer: submission closes the attempt, and `Attempt` refuses to close
    twice -- so the first save would have ended the exercise.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.provisioner.workspace_for(started.attempt.id).write_file("stub.py", FIRST)
    world.watcher.saves(2)

    drain(world, started.attempt.id)

    stored = world.attempts.get(started.attempt.id)
    assert stored is not None
    assert stored.is_active
    assert stored.verdict is None


def test_the_workspace_survives_a_preview() -> None:
    """`SubmitSolution` disposes of it on success; a preview must not, or the
    second save would have nothing to read.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    workspace = world.provisioner.workspace_for(started.attempt.id)
    workspace.write_file("stub.py", FIRST)
    world.watcher.saves()

    drain(world, started.attempt.id)

    assert not workspace.disposed


def test_the_grader_sees_the_source_through_the_attempt() -> None:
    """The in-memory event is real while the pass runs, which is what keeps
    `Grader.grade`'s contract true: a verdict is derived from a source the
    attempt remembers. `RecordingGrader` reads it off the aggregate, so this
    asserts the mechanism and not just the outcome.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.provisioner.workspace_for(started.attempt.id).write_file("stub.py", SECOND)
    world.watcher.saves()

    drain(world, started.attempt.id)

    assert world.recorder.calls[0][0] == SECOND


def test_a_failing_draft_carries_the_outcome_the_verdict_derives() -> None:
    """A preview of wrong code is a verdict like any other, and `Draft.outcome`
    reads it off the verdict rather than storing a second copy -- the same rule
    `Submission` follows.
    """
    world = an_environment(grader=RecordingGrader(a_failing_verdict()))
    started = a_start_attempt(world)(KATA)
    world.provisioner.workspace_for(started.attempt.id).write_file("stub.py", FIRST)
    world.watcher.saves()

    drafts = drain(world, started.attempt.id)

    assert drafts[0] is not None
    assert drafts[0].outcome is Outcome.FAIL


def test_a_tick_yields_nothing_to_report() -> None:
    """The `False` the watcher yields is how the web layer gets a chance to
    notice a reader that has gone away (`FileWatcher` in `domain/ports.py`).
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.provisioner.workspace_for(started.attempt.id).write_file("stub.py", FIRST)
    world.watcher.ticks(2).saves()

    drafts = drain(world, started.attempt.id)

    assert [draft is None for draft in drafts] == [True, True, False]
    assert len(world.recorder.calls) == 1


def test_a_save_caught_mid_write_is_skipped_rather_than_reported() -> None:
    """Editors save by writing a temporary file and renaming it over the target,
    so there is a window where the path is not readable -- and another event
    follows a few milliseconds later. A transient `FileNotFoundError` in front
    of a solver who did nothing wrong would be the wrong answer.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.watcher.saves()  # nothing has ever been written to stub.py

    drafts = drain(world, started.attempt.id)

    assert drafts == []
    assert world.recorder.calls == []


def test_it_watches_the_attempts_own_file() -> None:
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.watcher.ticks()

    drain(world, started.attempt.id)

    workspace = world.provisioner.workspace_for(started.attempt.id)
    assert world.watcher.watched == [workspace.resolve("stub.py")]


def test_submitting_from_elsewhere_ends_the_stream() -> None:
    """The attempt is re-read on every save, so a stream cannot go on grading an
    exercise that has finished -- and the sentence it ends with is the
    aggregate's own.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.provisioner.workspace_for(started.attempt.id).write_file("stub.py", FIRST)
    started.attempt.complete(a_failing_verdict(), at=world.clock.now())
    world.attempts.save(started.attempt)
    world.watcher.saves()

    with pytest.raises(AttemptStateError, match="completed"):
        drain(world, started.attempt.id)


def test_an_attempt_deleted_under_a_live_stream_is_reported() -> None:
    """The row goes away while the stream is open.

    `practice gc` cannot cause this -- it collects workspaces, not rows -- but a
    developer with a sqlite shell can, and the answer has to be the same
    sentence every other use case gives rather than a `NoneType` traceback in an
    event stream. The row is removed behind the port's back, because the port has
    no delete and should not grow one for a test.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.provisioner.workspace_for(started.attempt.id).write_file("stub.py", FIRST)
    world.watcher.saves()
    stream = a_watch_solution_file(world)(started.attempt.id)
    del world.attempts._attempts[started.attempt.id]

    async def collect() -> None:
        async for _ in stream:
            pass

    with pytest.raises(AttemptNotFoundError):
        asyncio.run(collect())


class TestItRefusesBeforeStreamingAnything:
    """The refusals are raised by the call, not by the first `__anext__`.

    That is why `__call__` is an ordinary method returning a generator rather
    than an `async def` generator: an async generator's body does not run until
    it is iterated, so a web layer would have committed to a 200 response
    before finding out the attempt does not exist.
    """

    def test_an_attempt_that_is_not_there(self) -> None:
        world = an_environment()

        with pytest.raises(AttemptNotFoundError):
            a_watch_solution_file(world)(MISSING)

    def test_a_finished_attempt(self) -> None:
        world = an_environment()
        started = a_start_attempt(world)(KATA)
        started.attempt.abandon(at=world.clock.now())
        world.attempts.save(started.attempt)

        with pytest.raises(AttemptStateError, match="abandoned"):
            a_watch_solution_file(world)(started.attempt.id)

    def test_an_exercise_that_left_the_library(self) -> None:
        world = an_environment()
        started = a_start_attempt(world)(KATA)
        world.content.forget(KATA)

        with pytest.raises(ExerciseNotFoundError):
            a_watch_solution_file(world)(started.attempt.id)

    def test_an_attempt_opened_in_interview_mode(self) -> None:
        """The refusal lands here as well as in `RevealSolutionFile` because
        both share `load_solution_file`, which is the whole reason that function
        exists: a page that offered the watch stream for an attempt whose file
        the other use case refuses would be a page with a button that does
        nothing.
        """
        world = an_environment()
        started = a_start_attempt(world)(KATA, mode=AttemptMode.INTERVIEW)

        with pytest.raises(PolicyViolationError, match="interview mode"):
            a_watch_solution_file(world)(started.attempt.id)

    def test_a_git_scenario(self) -> None:
        world = an_environment()
        started = a_start_attempt(world)(SCENARIO)

        with pytest.raises(UnsupportedExerciseKindError, match="no solution file"):
            a_watch_solution_file(world)(started.attempt.id)

    def test_a_workspace_that_has_been_collected(self) -> None:
        world = an_environment()
        started = a_start_attempt(world)(KATA)
        world.provisioner.collect(started.attempt.id)

        with pytest.raises(WorkspaceGoneError):
            a_watch_solution_file(world)(started.attempt.id)
