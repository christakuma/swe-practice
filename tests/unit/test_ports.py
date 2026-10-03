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
from practice.domain.review import Grade, ReviewCard
from practice.domain.scheduling import Sm2Scheduler
from tests.fakes import (
    BuilderRepoQueryFactory,
    FakeClock,
    FakeContentRepository,
    FakeProvisioner,
    FakeWorkspace,
    FixedScheduler,
    SequentialIdGenerator,
    StubKataRunner,
    a_kata,
    a_record,
    a_repo,
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
        RepoQuery,
        RepoQueryFactory,
        SandboxProvisioner,
        Scheduler,
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


def test_the_fake_provisioner_reports_what_it_has_provisioned() -> None:
    """The Phase 6 half of the port: `gc` asks for a listing, and the fake has to
    describe a workspace the way the real one does or the orphan rule is tested
    against a shape that does not occur.
    """
    provisioner = FakeProvisioner()
    exercise = a_kata()
    attempt_id = AttemptId.parse("00000001-0000-4000-8000-000000000000")
    provisioner.provision(exercise, attempt_id)

    (found,) = provisioner.workspaces()

    assert found.short_id == attempt_id.short
    assert found.attempt_id == attempt_id
    assert found.is_described is True


def test_a_stray_workspace_is_listed_with_no_attempt_behind_it() -> None:
    """What an interrupted provision leaves, and the only state that makes the
    orphan rule interesting: a `short_id` and no metadata at all.
    """
    provisioner = FakeProvisioner()
    provisioner.leave_stray("deadbeef")

    (found,) = provisioner.workspaces()

    assert found.short_id == "deadbeef"
    assert found.attempt_id is None
    assert found.is_described is False


def test_discarding_removes_a_workspace_from_the_listing() -> None:
    provisioner = FakeProvisioner()
    provisioner.leave_stray("deadbeef")

    provisioner.discard("deadbeef")

    assert provisioner.workspaces() == ()
    assert provisioner.discarded == ["deadbeef"]


def test_a_disposed_workspace_stops_being_listed() -> None:
    """An attempt disposing of its own workspace is why `gc` has nothing to do in
    the normal case, so the fake has to stop reporting one.
    """
    provisioner = FakeProvisioner()
    exercise = a_kata()
    attempt_id = AttemptId.parse("00000001-0000-4000-8000-000000000000")

    provisioner.provision(exercise, attempt_id).dispose()

    assert provisioner.workspaces() == ()


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


# --- the Phase 5 fake ------------------------------------------------------


def test_the_fake_repo_query_satisfies_the_repo_query_port() -> None:
    """The annotation is the test, as everywhere else in this file. Twenty-four
    methods is enough surface that a fake drifting out of shape is a question of
    when, and mypy is the only thing that notices — an adapter never subclasses
    its port, so there is no inheritance for Python to complain about.
    """
    repo = a_repo()
    first, second = repo.chain("add build script", "add parser")
    repo.branch("main", second)

    query: RepoQuery = repo.build()

    assert query.rev_parse("HEAD") == second
    assert query.rev_parse("HEAD~1") == first
    assert query.head_ref() == "refs/heads/main"
    assert query.is_ancestor(first, second) is True
    assert query.subject("main") == "add parser"
    assert query.aliases() == {"c1": first, "c2": second}


# --- the Phase 8 factory ---------------------------------------------------


def test_the_builder_factory_satisfies_the_repo_query_factory_port() -> None:
    """The second implementation `RepoQueryFactory` needs to exist at all (§13).

    The first is `GitRepoQuery` itself -- the class is the callable -- and this is
    what makes the grader's assembly and the inspection use case unit-testable with
    no git installed.
    """
    repo = a_repo()
    (only,) = repo.chain("add parser")
    repo.branch("main", only)

    factory: RepoQueryFactory = BuilderRepoQueryFactory(repo)

    assert factory(FakeWorkspace()).rev_parse("HEAD") == only


def test_the_builder_factory_hands_out_a_fresh_query_each_call() -> None:
    """The real factory's one load-bearing property, held by the double.

    `GitRepoQuery` caches every answer for the life of an instance, which is what
    makes six questions cost one `git` process. One instance shared across a
    solver's commands would answer the repo state panel with the repository as it
    was *before* the command that prompted the redraw -- a silent bug, and the
    reason this is a factory rather than a `RepoQuery` argument.
    """
    repo = a_repo()
    first, second = repo.chain("skeleton", "parser")
    repo.branch("main", first)
    factory = BuilderRepoQueryFactory(repo)
    assert factory(FakeWorkspace()).rev_parse("HEAD") == first

    repo.moved("refs/heads/main", second)

    assert factory(FakeWorkspace()).rev_parse("HEAD") == second


# --- the Phase 9 scheduler -------------------------------------------------


def test_the_sm2_scheduler_satisfies_the_scheduler_port() -> None:
    """The real one. `tests/unit/domain/scheduling/` is where its arithmetic is
    held to §9.7's properties; what this adds is the shape, which only mypy sees.
    """
    scheduler: Scheduler = Sm2Scheduler()
    now = FakeClock().now()
    card = ReviewCard.new(ExerciseId("katas/two-sum"), now.date())

    reviewed = scheduler.next_card(card, Grade.GOOD, now)

    assert reviewed.due_on > now.date()
    assert reviewed.last_reviewed_at == now


def test_the_fixed_scheduler_satisfies_it_too() -> None:
    """The second implementation §13 asks of the port, and the one the use-case
    tests drive: it records the grade it was handed instead of doing arithmetic
    those tests would then depend on.
    """
    scheduler: Scheduler = FixedScheduler(interval_days=3)
    card = ReviewCard.new(ExerciseId("katas/two-sum"), FakeClock().today())

    reviewed = scheduler.next_card(card, Grade.AGAIN, FakeClock().now())

    assert reviewed.interval_days == 3
    assert isinstance(scheduler, FixedScheduler)
    assert scheduler.grades == [Grade.AGAIN]
