"""The four lifecycle use cases: list, resume, abandon, collect.

One file rather than four, because they are one behaviour seen from four angles —
PLAN.md §8.1's rule that *an attempt is active until it is submitted or abandoned,
and its workspace lives exactly that long* — and the interesting assertions are the
ones that cross between them. "gc never deletes the workspace of an active attempt"
is a statement about `CollectWorkspaces` and `StartAttempt` together, and splitting
it across files would mean neither file contained it.

The two that say which attempt is *current* are in the same group and not in
this file: `test_current_attempt.py` has them, because every assertion about
them is about the two together and none is about a workspace.

The test that matters most is `test_gc_never_collects_the_workspace_of_an_active_
attempt`. It is the phase's exit criterion, it is the reason `gc` refused to delete
anything for three phases, and it is the one failure here that would destroy
someone's work rather than inconvenience them.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    WorkspaceGoneError,
)
from practice.application.use_cases import AbandonAttempt
from practice.domain.attempt import AttemptStatus
from practice.domain.errors import AttemptStateError
from practice.domain.ids import AttemptId, ExerciseId
from tests.unit.application.helpers import (
    a_collect_workspaces,
    a_list_open_attempts,
    a_passing_verdict,
    a_resume_attempt,
    a_start_attempt,
    an_abandon_attempt,
    an_environment,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from practice.domain.exercise import Exercise
    from practice.domain.ports import Workspace, WorkspaceSummary
    from tests.fakes import FakeProvisioner


class UndeletableProvisioner:
    """A `SandboxProvisioner` whose `discard` raises, and nothing else.

    A named class rather than a monkeypatched method so mypy still sees a
    provisioner where one is required, and delegating to a real `FakeProvisioner`
    so the only difference from the real thing is the one the test is about.
    """

    def __init__(self, inner: FakeProvisioner) -> None:
        self._inner = inner

    def provision(self, exercise: Exercise, attempt_id: AttemptId) -> Workspace:
        return self._inner.provision(exercise, attempt_id)

    def attach(
        self, exercise: Exercise, attempt_id: AttemptId
    ) -> Workspace | None:  # pragma: no cover - not reached by this test
        return self._inner.attach(exercise, attempt_id)

    def workspaces(
        self,
    ) -> Sequence[WorkspaceSummary]:  # pragma: no cover - ditto
        return self._inner.workspaces()

    def discard(self, short_id: str) -> None:
        del short_id
        raise RuntimeError("cannot delete the workspace")


KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")
MISSING = AttemptId.parse("deadbeef-0000-4000-8000-000000000000")


# --- listing what is open --------------------------------------------------


def test_nothing_is_open_before_anything_is_started() -> None:
    assert a_list_open_attempts(an_environment())() == ()


def test_an_open_attempt_is_listed_with_its_exercise_and_its_workspace() -> None:
    """The join is in the use case, not the caller: an `Attempt` holds an
    `ExerciseId` and rendering anything at all means another lookup, which done per
    caller is how a CLI command and a web route end up disagreeing about a deleted
    exercise (`dto.py`).
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)

    (found,) = a_list_open_attempts(world)()

    assert found.attempt.id == started.attempt.id
    assert found.exercise is not None
    assert found.exercise.id == KATA
    assert found.workspace_on_disk is True
    assert found.can_resume is True
    assert found.label == started.exercise.title


def test_a_submitted_attempt_leaves_the_list() -> None:
    """Which is the whole definition: active until submitted or abandoned."""
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    attempt = world.attempts.get(started.attempt.id)
    assert attempt is not None
    attempt.complete(a_passing_verdict(), at=world.clock.now())
    world.attempts.save(attempt)

    assert a_list_open_attempts(world)() == ()


def test_an_attempt_whose_workspace_is_gone_cannot_be_resumed() -> None:
    """And the listing says so, rather than letting `resume` be the thing that
    finds out. A prompt offering a choice that cannot be taken is worse than one
    that offers only the choice that can.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.provisioner.collect(started.attempt.id)

    (found,) = a_list_open_attempts(world)()

    assert found.workspace_on_disk is False
    assert found.can_resume is False


def test_an_attempt_whose_exercise_is_gone_is_still_listed() -> None:
    """The honest encoding rather than a convenience: an exercise can be renamed or
    deleted under a live attempt, and the result can be abandoned and never graded.
    A listing that hid it would hide the only thing left to do about it.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.content.forget(KATA)

    (found,) = a_list_open_attempts(world)()

    assert found.exercise is None
    assert found.can_resume is False
    assert "no longer in the library" in found.label
    assert str(started.attempt.exercise_id) in found.label


def test_open_attempts_come_back_oldest_first() -> None:
    world = an_environment()
    first = a_start_attempt(world)(KATA)
    world.clock.advance(timedelta(minutes=5))
    second = a_start_attempt(world)(SCENARIO)

    open_attempts = a_list_open_attempts(world)()

    assert [found.attempt.id for found in open_attempts] == [
        first.attempt.id,
        second.attempt.id,
    ]


# --- resuming ---------------------------------------------------------------


def test_resuming_hands_back_the_same_workspace() -> None:
    """Re-attach, never re-provision. A provisioner that rebuilt the fixture would
    hand back a pristine repository and silently discard the work (PLAN.md §8.1).
    """
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)

    resumed = a_resume_attempt(world)(started.attempt.id)

    assert resumed.workspace is started.workspace
    assert resumed.attempt.id == started.attempt.id
    assert resumed.exercise.id == SCENARIO


def test_resuming_writes_nothing() -> None:
    """Not even a `resumed` event. Opening a session again is not something the
    solver did, and the advisory checks in PLAN.md §6.3 read that log to decide
    whether someone reached for the reflog — every one of them would have to learn
    to ignore an entry that was not a command.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)

    a_resume_attempt(world)(started.attempt.id)

    stored = world.attempts.get(started.attempt.id)
    assert stored is not None
    assert stored.events == ()
    assert stored.status is AttemptStatus.ACTIVE
    assert stored.finished_at is None


def test_resuming_an_attempt_nobody_saved_is_refused() -> None:
    with pytest.raises(AttemptNotFoundError, match="no attempt with id"):
        a_resume_attempt(an_environment())(MISSING)


def test_resuming_a_finished_attempt_is_refused() -> None:
    """With its status in the message, because "already graded" and "abandoned" send
    someone to different places.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    an_abandon_attempt(world)(started.attempt.id)

    with pytest.raises(AttemptStateError, match="abandoned"):
        a_resume_attempt(world)(started.attempt.id)


def test_resuming_an_attempt_whose_exercise_is_gone_is_refused() -> None:
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.content.forget(KATA)

    with pytest.raises(ExerciseNotFoundError, match="no longer in the library"):
        a_resume_attempt(world)(started.attempt.id)


def test_resuming_an_attempt_whose_workspace_is_gone_is_refused() -> None:
    """`WorkspaceGoneError` rather than a fresh workspace: the attempt can be
    abandoned but never graded, which is the distinction the status flag exists for.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.provisioner.collect(started.attempt.id)

    with pytest.raises(WorkspaceGoneError, match="nothing to resume"):
        a_resume_attempt(world)(started.attempt.id)


# --- abandoning -------------------------------------------------------------


def test_abandoning_marks_the_attempt_and_deletes_the_workspace() -> None:
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)

    abandoned = an_abandon_attempt(world)(started.attempt.id)

    assert abandoned.attempt.status is AttemptStatus.ABANDONED
    assert abandoned.attempt.finished_at == world.clock.now()
    assert world.provisioner.discarded == [started.attempt.id.short]
    assert a_list_open_attempts(world)() == ()


def test_abandoning_keeps_the_attempt_and_its_log() -> None:
    """The row stays, marked. The history is the point: an attempt someone walked
    away from is as much of a fact as one they finished.
    """
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)
    attempt = world.attempts.get(started.attempt.id)
    assert attempt is not None
    attempt.reveal_next_hint(at=world.clock.now())
    world.attempts.save(attempt)

    an_abandon_attempt(world)(started.attempt.id)

    stored = world.attempts.get(started.attempt.id)
    assert stored is not None
    assert stored.status is AttemptStatus.ABANDONED
    assert stored.hints_revealed == 1


def test_abandoning_saves_the_row_before_deleting_the_workspace() -> None:
    """The asymmetry `StartAttempt` reasons about, from the other end. A workspace
    with no active attempt is what gc collects; a deleted workspace under an attempt
    still marked active is a session the prompt keeps offering and nothing can
    resume. So the recoverable failure is the one to risk.

    Asserted by failing the delete: the row must already be written.
    """
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)
    abandon = AbandonAttempt(
        content=world.content,
        attempts=world.attempts,
        provisioner=UndeletableProvisioner(world.provisioner),
        clock=world.clock,
    )

    with pytest.raises(RuntimeError, match="cannot delete"):
        abandon(started.attempt.id)

    stored = world.attempts.get(started.attempt.id)
    assert stored is not None
    assert stored.status is AttemptStatus.ABANDONED


def test_an_attempt_whose_exercise_is_gone_can_still_be_abandoned() -> None:
    """The way out of the one state nothing else can fix. `Workspace.dispose` needs
    an `Exercise` to attach with, and this is precisely the case where there is
    none — which is why `discard` takes the directory name instead.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.content.forget(KATA)

    abandoned = an_abandon_attempt(world)(started.attempt.id)

    assert abandoned.exercise is None
    assert abandoned.attempt.status is AttemptStatus.ABANDONED
    assert world.provisioner.discarded == [started.attempt.id.short]


def test_abandoning_twice_is_refused() -> None:
    """Not idempotent on purpose: a mistyped id that silently succeeded against a
    *completed* attempt would throw away a graded workspace.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    an_abandon_attempt(world)(started.attempt.id)

    with pytest.raises(AttemptStateError, match="abandoned"):
        an_abandon_attempt(world)(started.attempt.id)


def test_abandoning_an_attempt_nobody_saved_is_refused() -> None:
    with pytest.raises(AttemptNotFoundError, match="no attempt with id"):
        an_abandon_attempt(an_environment())(MISSING)


# --- collecting -------------------------------------------------------------


def test_gc_never_collects_the_workspace_of_an_active_attempt() -> None:
    """**The phase's exit criterion, and the reason gc refused to delete anything
    for three phases.** An orphan is a workspace with no corresponding `active`
    attempt row (PLAN.md §8.1); without the table there was no way to tell one from
    the workspace of a session open in another tab.

    Asserted with the delete actually requested, because a test that only checked
    the classification would pass against a `discard` loop that ignored it.
    """
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)

    collected = a_collect_workspaces(world)(delete=True)

    assert collected.deleted == ()
    assert world.provisioner.discarded == []
    assert [state.workspace.short_id for state in collected.in_use] == [
        started.attempt.id.short
    ]
    assert a_resume_attempt(world)(started.attempt.id).workspace is started.workspace


def test_a_workspace_with_no_active_attempt_is_an_orphan() -> None:
    world = an_environment()
    world.provisioner.leave_stray("deadbeef")

    collected = a_collect_workspaces(world)()

    (orphan,) = collected.orphans
    assert orphan.workspace.short_id == "deadbeef"
    assert orphan.is_orphan is True
    assert orphan.workspace.is_described is False


def test_an_undescribed_workspace_is_collected_like_any_other() -> None:
    """Because the rule is decided on the directory name, not on the metadata. The
    most interesting leftover is an interrupted provision, which has no `attempt_id`
    to join on — and under a metadata-based rule would be both unexplainable and
    uncollectable.
    """
    world = an_environment()
    world.provisioner.leave_stray("deadbeef")

    collected = a_collect_workspaces(world)(delete=True)

    assert collected.deleted == ("deadbeef",)
    assert world.provisioner.discarded == ["deadbeef"]
    assert a_collect_workspaces(world)().workspaces == ()


def test_the_workspace_of_a_submitted_attempt_is_an_orphan() -> None:
    """The ordinary way one appears: a process was killed between grading and
    disposal. The attempt is completed, so nothing owns the directory.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    attempt = world.attempts.get(started.attempt.id)
    assert attempt is not None
    attempt.complete(a_passing_verdict(), at=world.clock.now())
    world.attempts.save(attempt)

    collected = a_collect_workspaces(world)(delete=True)

    assert collected.deleted == (started.attempt.id.short,)


def test_a_dry_run_classifies_exactly_what_a_real_run_deletes() -> None:
    """One use case with a flag rather than two, because a `--dry-run` that listed
    one set and a real run that deleted another is the bug that makes a destructive
    command untrustworthy.
    """
    world = an_environment()
    a_start_attempt(world)(KATA)
    world.provisioner.leave_stray("deadbeef")
    collect = a_collect_workspaces(world)

    reported = collect()
    deleted = collect(delete=True)

    assert [state.workspace.short_id for state in reported.orphans] == ["deadbeef"]
    assert deleted.deleted == ("deadbeef",)
    assert reported.workspaces == deleted.workspaces


def test_a_dry_run_deletes_nothing() -> None:
    world = an_environment()
    world.provisioner.leave_stray("deadbeef")

    collected = a_collect_workspaces(world)()

    assert collected.deleted == ()
    assert world.provisioner.discarded == []


def test_the_collection_reports_what_collecting_would_free() -> None:
    """The number worth printing, and not the same as the total: most of the bytes
    under the workspace root usually belong to a session that is still open.
    """
    world = an_environment()
    a_start_attempt(world)(KATA)
    world.provisioner.leave_stray("deadbeef")

    collected = a_collect_workspaces(world)()

    assert collected.total_bytes == 1024 + 512
    assert collected.reclaimable_bytes == 512


def test_an_empty_workspace_root_collects_nothing() -> None:
    collected = a_collect_workspaces(an_environment())(delete=True)

    assert collected.workspaces == ()
    assert collected.deleted == ()
    assert collected.total_bytes == 0
