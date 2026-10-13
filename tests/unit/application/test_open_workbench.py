"""Loading an attempt for a page, in whatever state the attempt is in.

The distinction this use case exists for is in
`test_a_finished_attempt_loads_with_no_workspace`: `ResumeAttempt` refuses one,
and a URL has to render it. Everything else here is the shared half, tested
against the same fakes so the two cannot drift about what "the exercise is gone"
means.
"""

from __future__ import annotations

import pytest

from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    WorkspaceGoneError,
)
from practice.domain.exercise import KataSpec
from practice.domain.ids import AttemptId, ExerciseId
from tests.unit.application.helpers import (
    a_mark_current_attempt,
    a_passing_verdict,
    a_start_attempt,
    a_submit_solution,
    an_environment,
    an_open_workbench,
)

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")

STUB = "def two_sum(values, target):\n    ...\n"


def test_an_active_attempt_loads_with_its_live_workspace() -> None:
    world = an_environment()
    started = a_start_attempt(world)(KATA)

    workbench = an_open_workbench(world)(started.attempt.id)

    assert workbench.is_active
    assert workbench.exercise.id == KATA
    assert workbench.workspace is world.provisioner.workspace_for(started.attempt.id)


def test_a_kata_seeds_the_editor_from_the_workspace_stub() -> None:
    """From the workspace, not the library, and the difference is not academic.

    The stub is copied in when the attempt is provisioned, so what is there is
    what *this* attempt started from. Reading the library instead would reseed an
    open attempt with a stub edited since, silently.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    spec = started.exercise.spec
    assert isinstance(spec, KataSpec)
    world.provisioner.workspace_for(started.attempt.id).write_file(spec.stub, STUB)

    workbench = an_open_workbench(world)(started.attempt.id)

    assert workbench.editor_source == STUB
    assert workbench.has_editor


def test_a_kata_whose_stub_is_missing_still_loads() -> None:
    """A workbench is the wrong place to discover a malformed exercise.

    `practice validate` and the content suite are what hold a kata to shipping a
    stub; a page that refused to open would report a library problem as a broken
    attempt, and the solver cannot do anything about either from here.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)

    workbench = an_open_workbench(world)(started.attempt.id)

    assert workbench.editor_source is None
    assert not workbench.has_editor


def test_a_git_scenario_has_no_editor() -> None:
    """`None` rather than an empty string: its surface is a console, not a buffer.

    An empty string would be an editor that happens to be blank, and the template
    asks exactly one question of this field -- is there an editor on this page.
    """
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)

    workbench = an_open_workbench(world)(started.attempt.id)

    assert workbench.editor_source is None
    assert workbench.workspace is not None


def test_a_finished_attempt_loads_with_no_workspace() -> None:
    """The case this use case exists for, and the one `ResumeAttempt` refuses.

    Submission disposes of the workspace -- §8.1 ties its lifetime to `ACTIVE` --
    so `None` here is the expected state and not a failure. A page that raised on
    it could never show a verdict, which is the only thing a finished attempt has
    left to show.
    """
    world = an_environment(grader=None)
    started = a_start_attempt(world)(KATA)
    a_submit_solution(world)(started.attempt.id, source="def two_sum(): ...")

    workbench = an_open_workbench(world)(started.attempt.id)

    assert not workbench.is_active
    assert workbench.workspace is None
    assert workbench.editor_source is None
    assert workbench.verdict == a_passing_verdict()


def test_an_active_attempt_whose_workspace_was_collected_is_refused() -> None:
    """Still `WorkspaceGoneError`, exactly as resuming is.

    The attempt can be abandoned and never graded, and a page that quietly
    rendered an editor over nothing would invite work that cannot be submitted.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.provisioner.collect(started.attempt.id)

    with pytest.raises(WorkspaceGoneError, match="abandon it"):
        an_open_workbench(world)(started.attempt.id)


def test_an_unknown_attempt_is_refused() -> None:
    world = an_environment()

    with pytest.raises(AttemptNotFoundError):
        an_open_workbench(world)(
            AttemptId.parse("00000000-0000-4000-8000-000000000000")
        )


def test_an_exercise_that_left_the_library_is_refused() -> None:
    """Same message as `ResumeAttempt`'s, because it is the same remedy.

    `dto.py` makes the argument for the join living in the application layer: two
    callers doing it themselves is how a CLI command and a web route end up
    disagreeing about what to do when the exercise has been deleted.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.content.forget(KATA)

    with pytest.raises(ExerciseNotFoundError, match="no longer in the library"):
        an_open_workbench(world)(started.attempt.id)


def test_loading_a_workbench_writes_nothing() -> None:
    """A read, like resuming. No event, no timestamp, no status change.

    Opening a page again is not something the solver did in the exercise, and the
    process assertions of §6.3 read the event log to decide whether someone
    reached for the reflog -- an entry per page load would make every advisory
    check learn to ignore one kind of entry.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    before = len(started.attempt.events)

    workbench = an_open_workbench(world)(started.attempt.id)

    assert len(workbench.attempt.events) == before
    assert workbench.attempt.status is started.attempt.status


def test_loading_a_workbench_does_not_make_it_the_current_attempt() -> None:
    """Not even that (ADR 0026). A page loaded is not a page looked at: a link
    opened in a background tab would take the mark from the attempt on screen,
    so the page reports coming to the front and `MarkCurrentAttempt` hears it.
    """
    world = an_environment()
    older = a_start_attempt(world)(KATA)
    newer = a_start_attempt(world)(SCENARIO)
    a_mark_current_attempt(world)(newer.attempt.id)

    an_open_workbench(world)(older.attempt.id)

    assert world.attempts.current() == newer.attempt.id
