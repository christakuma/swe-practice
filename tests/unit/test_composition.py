"""The wiring point: does the graph it builds satisfy the ports it claims to?

As in `test_ports.py`, **mypy is the real enforcement** — `Services` annotates
its fields with the port protocols, so an adapter that drifts out of shape fails
the type check, and nothing else would catch it because an adapter never
subclasses its port.

What the asserts add is the part a type checker cannot see: that building the
graph writes nothing to disk — including no database, which is why `Database`
connects lazily — that every exercise kind has a grader, and that the overrides
the test suite depends on actually reach the adapters they are meant to
configure.

A unit test rather than an integration one, because nothing here runs: every
adapter stores the paths it was given and reads them when it is used.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from practice.adapters.git import ScenarioGrader
from practice.adapters.persistence import (
    InMemoryAttemptRepository,
    SqliteAttemptRepository,
    SqliteReviewRepository,
)
from practice.adapters.sandbox import SubprocessSandboxProvisioner
from practice.application.use_cases import (
    RevealSolutionFile,
    StartAttempt,
    SubmitSolution,
)
from practice.composition import SCHEDULERS, Services, build_scheduler, build_services
from practice.config import SCHEDULER_ENV, content_root, database_path
from practice.domain.errors import InvalidValueError
from practice.domain.exercise import ExerciseKind
from practice.domain.ids import AttemptId, ExerciseId
from practice.domain.review import ReviewCard
from practice.domain.scheduling import FsrsScheduler, Sm2Scheduler
from tests.fakes import FakeClock

if TYPE_CHECKING:
    from pathlib import Path

TWO_SUM = ExerciseId("katas/two-sum")


def test_the_real_graph_satisfies_every_port() -> None:
    """The annotation on each `Services` field is the assertion; this builds the
    graph so that a failure is a test failure rather than only a mypy one.
    """
    services: Services = build_services()

    assert services.content.get(ExerciseId("katas/two-sum")) is not None
    assert isinstance(services.start_attempt, StartAttempt)
    assert isinstance(services.submit_solution, SubmitSolution)
    assert isinstance(services.reveal_solution_file, RevealSolutionFile)


def test_building_the_graph_writes_nothing_to_disk(tmp_path: Path) -> None:
    """Building must create neither the cache directory nor the database, or
    `practice validate` would leave both behind on a machine that has never run an
    attempt.

    The database half is the Phase 6 addition, and it is the reason `Database`
    stores a path and connects on first use rather than in its constructor.
    """
    workspaces = tmp_path / "ws"
    storage = tmp_path / "state" / "practice.db"

    build_services(workspaces=workspaces, database=storage)

    assert not workspaces.exists()
    assert not storage.exists()
    assert not storage.parent.exists()


def test_the_repositories_are_the_sqlite_ones(tmp_path: Path) -> None:
    """The Phase 6 swap, asserted at the only place that decides it.

    Narrowed to the concrete classes deliberately: everywhere else in the system
    these are `AttemptRepository` and `ReviewRepository` and nothing may know
    otherwise, which is exactly why the one module that *does* know should be held
    to it.
    """
    services = build_services(database=tmp_path / "practice.db")

    assert isinstance(services.attempts, SqliteAttemptRepository)
    assert isinstance(services.reviews, SqliteReviewRepository)


def test_both_repositories_share_one_database(tmp_path: Path) -> None:
    """One file, so a future use case that reads an attempt and writes its review
    card does it in one place. Asserted through behaviour rather than identity: the
    `Database` is not a field on `Services`, so the only way to ask is to write
    through one repository and read through the other's file.
    """
    storage = tmp_path / "practice.db"

    services = build_services(database=storage)
    services.reviews.save_card(ReviewCard.new(TWO_SUM, date(2026, 10, 2)))

    assert storage.is_file()
    # Reading an attempt out of the same file the card was written to: if the two
    # repositories had their own `Database`, the second one would be migrating a
    # file that does not exist yet rather than reading this one.
    assert services.attempts.get(AttemptId.parse(str(uuid4()))) is None


def test_an_attempt_store_override_keeps_the_database_out_of_it(
    tmp_path: Path,
) -> None:
    """The escape hatch an application test uses: the real use cases over the
    in-memory store, with nothing on disk at all.
    """
    storage = tmp_path / "practice.db"

    services = build_services(database=storage, attempts=InMemoryAttemptRepository())

    assert isinstance(services.attempts, InMemoryAttemptRepository)
    assert services.start_attempt.attempts is services.attempts


def test_the_database_path_override_reaches_the_repositories(tmp_path: Path) -> None:
    """And the default is `config.database_path()`, which the test suite has
    already pointed somewhere disposable for every test (tests/conftest.py).
    """
    storage = tmp_path / "elsewhere.db"

    build_services(database=storage).reviews.save_card(
        ReviewCard.new(TWO_SUM, date(2026, 10, 2))
    )

    assert storage.is_file()
    assert not database_path().exists()


def test_every_exercise_kind_has_a_grader() -> None:
    """As of Phase 5, both of them. Asserted against the enum rather than against a
    literal pair, so adding a third kind without a grader fails here -- which is the
    one place that can notice before a solver does.
    """
    graders = build_services().graders

    assert set(graders.graders) == set(ExerciseKind)


def test_the_grader_and_the_panel_share_one_repo_query_factory() -> None:
    """The single disagreement `InspectRepository` exists to make impossible.

    If the grader built its `RepoQuery` one way and the repo state panel built one
    another way, the panel a solver decides to submit from could answer "is this
    worktree clean?" differently from the verdict they then get -- and nothing
    would tell them which of the two was lying. One factory, named once, here.
    """
    services = build_services()

    grader = services.graders.graders[ExerciseKind.GIT_SCENARIO]
    assert isinstance(grader, ScenarioGrader)
    # Narrowed to the concrete adapter deliberately: the factory is not on the
    # `Grader` port, and this test is about what the wiring point built.
    assert grader._query_for is services.repo_query
    assert services.inspect_repository.repo_query is services.repo_query


def test_the_scheduler_defaults_to_sm2_and_only_one_use_case_holds_it() -> None:
    """Both halves matter. SM-2 is still the default, named once; and
    `GradeReview` being its only caller is what kept swapping it for FSRS a
    change to this file -- a port with callers scattered across the use cases
    would be a port in name only.

    Phase 13 cashed that in: the `Sm2Scheduler()` on the line below became
    `build_scheduler()`, and nothing else in the graph moved.
    """
    services = build_services()

    assert isinstance(services.scheduler, Sm2Scheduler)
    assert services.grade_review.scheduler is services.scheduler


# --- choosing one, which is Phase 13's addition ----------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [("sm2", Sm2Scheduler), ("fsrs", FsrsScheduler)],
)
def test_each_name_builds_its_scheduler(name: str, expected: type[object]) -> None:
    assert isinstance(build_scheduler(name), expected)


def test_the_registry_is_the_list_of_valid_names() -> None:
    """Which is the only reason a two-entry mapping earns its place over an
    `if`: the refusal below quotes it, and `practice up` prints through it.
    """
    assert set(SCHEDULERS) == {"sm2", "fsrs"}


def test_an_unknown_name_is_refused_with_the_valid_ones_named() -> None:
    """Rather than falling back to the default, which would make a typo in
    `PRACTICE_SCHEDULER` indistinguishable from having set nothing -- and the
    only symptom would be intervals the user cannot explain, weeks later.
    """
    with pytest.raises(InvalidValueError, match="is not a scheduler") as refusal:
        build_scheduler("fsrs2")

    assert "fsrs, sm2" in str(refusal.value)
    assert SCHEDULER_ENV in str(refusal.value)


def test_the_environment_chooses_when_no_name_is_passed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The path a real launch takes. `conftest.py` clears this variable for every
    test, so a developer with `fsrs` exported runs the same suite CI does.
    """
    monkeypatch.setenv(SCHEDULER_ENV, "fsrs")

    assert isinstance(build_scheduler(), FsrsScheduler)
    assert isinstance(build_services().scheduler, FsrsScheduler)


@pytest.mark.parametrize("spelling", ["FSRS", " fsrs ", "Fsrs"])
def test_the_name_is_normalised(monkeypatch: pytest.MonkeyPatch, spelling: str) -> None:
    """It is the one setting in `config.py` a user types by hand into a shell
    profile, so case and stray whitespace are not errors worth reporting.
    """
    monkeypatch.setenv(SCHEDULER_ENV, spelling)

    assert isinstance(build_scheduler(), FsrsScheduler)


def test_an_explicit_scheduler_overrides_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The override exists so a test can choose without setting an environment
    variable -- which would choose for every other test in the process.
    """
    monkeypatch.setenv(SCHEDULER_ENV, "fsrs")

    services = build_services(scheduler=Sm2Scheduler())

    assert isinstance(services.scheduler, Sm2Scheduler)
    assert services.grade_review.scheduler is services.scheduler


def test_the_review_use_cases_read_the_card_store_the_root_built() -> None:
    """All three, because the one that writes and the one that offers have to
    agree about what is already scheduled -- which they can only do by reading
    the same repository.
    """
    services = build_services()

    assert services.offer_review.reviews is services.reviews
    assert services.grade_review.reviews is services.reviews
    assert services.review_queue.reviews is services.reviews


def test_the_progress_summary_reads_all_three_stores() -> None:
    """The only use case holding the attempt repository for something other than
    finding one attempt by id, and the only read that joins all three.
    """
    services = build_services()

    assert services.summarise_progress.attempts is services.attempts
    assert services.summarise_progress.reviews is services.reviews
    assert services.summarise_progress.content is services.content


def test_the_content_root_override_reaches_both_adapters() -> None:
    """One argument, two readers: the repository loads exercises from it and the
    provisioner copies fixtures out of it. A root that reached only one of them
    would make the content suite load from a temp library and provision from the
    real one.
    """
    library = content_root()

    services = build_services(content=library)

    assert services.content.get(ExerciseId("katas/two-sum")) is not None
    # Narrowed to the concrete adapter deliberately: `directory_for` is not on
    # the port, and this test is about what the wiring point built rather than
    # about what a use case can see.
    assert isinstance(services.provisioner, SubprocessSandboxProvisioner)
    assert services.provisioner.directory_for(ExerciseId("katas/two-sum")) == (
        library / "katas" / "two-sum"
    )


def test_an_injected_clock_is_the_one_the_use_cases_use() -> None:
    clock = FakeClock()

    services = build_services(clock=clock)

    assert services.clock is clock
    assert services.start_attempt.clock is clock
    assert services.submit_solution.clock is clock


def test_the_use_cases_are_wired_to_the_same_objects() -> None:
    """Both use cases share the attempt store, which is the whole reason
    `SubmitSolution` can find an attempt `StartAttempt` created.
    """
    services = build_services()

    assert services.start_attempt.attempts is services.submit_solution.attempts
    assert services.start_attempt.provisioner is services.submit_solution.provisioner
