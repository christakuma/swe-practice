"""Port conformance.

The real enforcement here is **mypy**, not the asserts. Each fake is assigned to a
variable annotated with the port it claims to satisfy, and under `--strict` a fake
that drifts out of shape fails the type check. Protocols are structural, so
nothing else would catch it: an adapter never subclasses its port, so there is no
inheritance for Python to complain about at import time.

`typing.runtime_checkable` plus `isinstance` was the alternative and is close to
worthless for this — it checks that the attribute names exist, not that the
signatures match, so a fake whose `now()` took an argument would pass.

The asserts that follow the annotations cover the behaviour a test double is
expected to have, which mypy cannot see: that time only moves when a test moves
it, and that ids are readable in a failure message.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from practice.adapters.persistence import InMemoryAttemptRepository
from practice.domain.attempt import Attempt, AttemptPolicy
from practice.domain.exercise import ExerciseFilter, ExerciseKind, KataSpec
from practice.domain.ids import AttemptId, ExerciseId, Sha
from practice.domain.ports import CommitInfo, ReflogEntry, WorktreeStatus
from tests.fakes import (
    FakeClock,
    FakeContentRepository,
    FakeProvisioner,
    FakeWorkspace,
    SequentialIdGenerator,
    StubKataRunner,
    a_kata,
    a_record,
    a_run,
    a_scenario,
)

if TYPE_CHECKING:
    from practice.adapters.kata import KataRunner
    from practice.domain.ports import (
        AttemptRepository,
        Clock,
        ContentRepository,
        IdGenerator,
        SandboxProvisioner,
        Workspace,
    )

C1 = Sha("1" * 40)
C2 = Sha("2" * 40)
T1 = Sha("a" * 40)


def test_fake_clock_satisfies_the_clock_port() -> None:
    clock: Clock = FakeClock(datetime(2026, 9, 30, 9, 0, tzinfo=UTC))

    assert clock.now() == datetime(2026, 9, 30, 9, 0, tzinfo=UTC)
    assert clock.today() == date(2026, 9, 30)


def test_a_fake_clock_stands_still_until_it_is_advanced() -> None:
    clock = FakeClock(datetime(2026, 9, 30, 9, 0, tzinfo=UTC))

    first = clock.now()
    assert clock.now() == first

    assert clock.advance(timedelta(minutes=5)) == datetime(
        2026, 9, 30, 9, 5, tzinfo=UTC
    )
    assert clock.now() == datetime(2026, 9, 30, 9, 5, tzinfo=UTC)


def test_a_fake_clock_refuses_to_run_backwards() -> None:
    with pytest.raises(ValueError, match="backwards"):
        FakeClock().advance(timedelta(minutes=-1))


def test_a_fake_clock_refuses_a_naive_datetime() -> None:
    """A fake that could hand over a naive datetime would only ever be used to
    write a test that does not reflect production, since `Attempt` rejects them.
    """
    with pytest.raises(ValueError, match="aware"):
        FakeClock(datetime(2026, 9, 30, 9, 0))  # noqa: DTZ001


def test_sequential_id_generator_satisfies_the_id_generator_port() -> None:
    ids: IdGenerator = SequentialIdGenerator()

    first = ids.new_attempt_id()
    second = ids.new_attempt_id()

    assert str(first) == "00000000-0000-0000-0000-000000000001"
    assert str(second) == "00000000-0000-0000-0000-000000000002"
    assert first != second


def test_generated_ids_have_a_usable_short_form() -> None:
    assert SequentialIdGenerator(start=0xABCDEF).new_attempt_id().short == "00000000"


class TestWorktreeStatus:
    """The `worktree_clean` default lives on the status object rather than in the
    assertion, so both RepoQuery implementations answer it identically.
    """

    def test_an_empty_status_is_clean_and_pristine(self) -> None:
        status = WorktreeStatus()

        assert status.is_clean is True
        assert status.is_pristine is True

    def test_untracked_files_alone_do_not_make_it_dirty(self) -> None:
        """A scratch file someone created while poking around must not fail them
        (PLAN.md §6.5).
        """
        status = WorktreeStatus(untracked=frozenset({"notes.txt"}))

        assert status.is_clean is True
        assert status.is_pristine is False

    @pytest.mark.parametrize("field_name", ["staged", "unstaged", "unmerged"])
    def test_anything_else_makes_it_dirty(self, field_name: str) -> None:
        status = WorktreeStatus(**{field_name: frozenset({"parser.py"})})

        assert status.is_clean is False
        assert status.is_pristine is False


class TestCommitInfo:
    def test_a_commit_with_two_parents_is_a_merge(self) -> None:
        commit = CommitInfo(sha=C1, tree=T1, subject="merge", parents=(C1, C2))

        assert commit.is_merge is True

    @pytest.mark.parametrize("parents", [(), (C1,)])
    def test_a_root_or_ordinary_commit_is_not(self, parents: tuple[Sha, ...]) -> None:
        commit = CommitInfo(sha=C2, tree=T1, subject="add parser", parents=parents)

        assert commit.is_merge is False


def test_a_reflog_entry_records_the_position_it_came_from() -> None:
    entry = ReflogEntry(index=3, sha=C1, message="reset: moving to HEAD~2")

    assert entry.index == 3
    assert entry.sha == C1


# --- the Phase 4 fakes -----------------------------------------------------


def test_the_fake_workspace_satisfies_the_workspace_port() -> None:
    """Both halves of the trust split, which is what the annotation checks: a
    fake that implemented `run` and not `run_tool` would no longer be a
    `Workspace`, and the kata engine would be the thing that found out.
    """
    workspace: Workspace = FakeWorkspace({"stub.py": "..."})

    assert workspace.read_file("stub.py") == "..."
    assert workspace.run(["git", "status"], timeout=1).succeeded
    assert workspace.run_tool(["python", "-m", "pytest"], timeout=1).succeeded


def test_the_fake_workspace_raises_an_oserror_for_a_missing_file() -> None:
    """Held to the real adapter's behaviour deliberately: `PytestKataRunner`
    reads a report that may not be there and catches `OSError` to mean "the
    suite did not run". A `KeyError` would sail straight past that.
    """
    with pytest.raises(OSError, match=r"report\.json"):
        FakeWorkspace().read_file("report.json")


def test_the_fake_provisioner_satisfies_the_provisioner_port() -> None:
    provisioner: SandboxProvisioner = FakeProvisioner()
    exercise = a_kata()
    attempt_id = AttemptId.parse("00000001-0000-4000-8000-000000000000")

    provisioned = provisioner.provision(exercise, attempt_id)

    assert provisioner.attach(exercise, attempt_id) is provisioned


def test_the_fake_provisioner_returns_none_for_a_workspace_that_is_not_there() -> None:
    """What the real one does, and what `SubmitSolution` turns into
    `WorkspaceGoneError`. A fake that raised instead would make that branch
    untestable and the test that covers it a fiction.
    """
    provisioner = FakeProvisioner()
    exercise = a_kata()
    attempt_id = AttemptId.parse("00000001-0000-4000-8000-000000000000")

    assert provisioner.attach(exercise, attempt_id) is None

    provisioner.provision(exercise, attempt_id)
    provisioner.collect(attempt_id)

    assert provisioner.attach(exercise, attempt_id) is None


def test_the_fake_content_repository_satisfies_the_content_port() -> None:
    content: ContentRepository = FakeContentRepository([a_kata(), a_scenario()])

    assert content.get(ExerciseId("katas/two-sum")) is not None
    assert content.get(ExerciseId("katas/nope")) is None
    assert [str(exercise.id) for exercise in content.list_exercises()] == [
        "git/revert-a-pushed-commit",
        "katas/two-sum",
    ]


def test_the_fake_content_repository_filters_through_the_domain() -> None:
    """It delegates to `ExerciseFilter.matches` rather than comparing fields
    itself, so it cannot disagree with the filesystem repository about what a
    filter means — which is the drift that stops a fake being evidence (§4.2).
    """
    content = FakeContentRepository([a_kata(), a_scenario()])

    katas = content.list_exercises(ExerciseFilter(kinds=frozenset({ExerciseKind.KATA})))

    assert [str(exercise.id) for exercise in katas] == ["katas/two-sum"]


def test_the_in_memory_attempt_repository_satisfies_the_attempt_port() -> None:
    """The real adapter, annotated as its port — the other half of the §13 rule,
    since a port whose only implementation is a fake has not been shown to work.
    """
    attempts: AttemptRepository = InMemoryAttemptRepository()
    exercise = a_kata()
    attempt = Attempt(
        attempt_id=AttemptId.parse("00000001-0000-4000-8000-000000000000"),
        exercise_id=exercise.id,
        policy=AttemptPolicy.for_exercise(exercise),
        started_at=FakeClock().now(),
    )

    attempts.save(attempt)

    assert attempts.get(attempt.id) is not None
    assert len(attempts.history_for(exercise.id)) == 1


def test_the_stub_kata_runner_satisfies_what_the_grader_needs() -> None:
    runner: KataRunner = StubKataRunner(a_run(a_record("test_one")))
    exercise = a_kata()
    assert isinstance(exercise.spec, KataSpec)

    run = runner.run(FakeWorkspace(), exercise.spec, "source")

    assert [record.name for record in run.tests] == ["test_one"]
