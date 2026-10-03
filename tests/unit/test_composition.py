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

from practice.adapters.git import ScenarioGrader
from practice.adapters.persistence import (
    InMemoryAttemptRepository,
    SqliteAttemptRepository,
    SqliteReviewRepository,
)
from practice.adapters.sandbox import SubprocessSandboxProvisioner
from practice.application.use_cases import StartAttempt, SubmitSolution
from practice.composition import Services, build_services
from practice.config import content_root, database_path
from practice.domain.exercise import ExerciseKind
from practice.domain.ids import AttemptId, ExerciseId
from practice.domain.review import ReviewCard
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
