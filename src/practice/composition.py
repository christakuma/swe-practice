"""The single wiring point: the only module that imports across every layer.

Manual dependency injection, no framework, no decorators, no magic — you can
read the whole object graph in one file, which is the property PLAN.md §3 claims
and this file either keeps or breaks.

**Why it arrives in Phase 4 and not Phase 0.** A wiring module with one adapter in
it is the abstraction §13 says to delete rather than carry, so Phase 2
deliberately did without one. Phase 4 was the first time there was a graph: a
content repository, a provisioner, an attempt store, a runner behind a grader
behind a registry, a clock and an id generator, assembled into two use cases.
Six objects with four edges between them is exactly when a reader benefits from
one place that shows the shape. Phase 5 adds a second grader and two more use
cases to it and changes nothing else, which is the return on having written it.

**`Services` holds ports, not implementations.** The annotations are the port
protocols, so mypy checks at the only place it can that each adapter still
satisfies the port it is being passed as — an adapter never subclasses its port
(ADR 0002), so nothing else would notice a drift. The attribute types being
protocols is also what lets a test build a `Services` out of fakes and drive the
real use cases with it.

It is also why the `Database` is *not* a field. It is machinery rather than a
dependency any use case has — the two repositories hold it, nothing else asks it
anything — and putting a concrete class on a dataclass of protocols would make
"these are all ports" the kind of claim with one exception in it. A caller that
wants to tell someone where the database is asks `config.database_path()`, which
is the question it is actually asking.

The three path arguments exist because the test suite needs to point at a
disposable library, a disposable workspace root and a disposable database.
Everything else comes from `config`, which is the module that knows where things
live on this machine.

**Phase 6's swap was one line per repository, which was the thing being tested.**
PLAN.md §11 put it this way: if the ports have been respected, exchanging the
in-memory stores for SQLite ones is a change to this file and nothing else — and
if it is not, that is the finding. It was. No use case, no grader and no CLI
command changed, because none of them had ever held anything but an
`AttemptRepository`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.adapters.clock import SystemClock
from practice.adapters.content import FilesystemContentRepository
from practice.adapters.git import GitRepoQuery, ScenarioGrader
from practice.adapters.ids import Uuid4IdGenerator
from practice.adapters.kata import KataGrader, PytestKataRunner
from practice.adapters.persistence import (
    Database,
    SqliteAttemptRepository,
    SqliteReviewRepository,
)
from practice.adapters.sandbox import (
    SubprocessEditorLauncher,
    SubprocessSandboxProvisioner,
)
from practice.application.registry import GraderRegistry
from practice.application.use_cases import (
    AbandonAttempt,
    CollectWorkspaces,
    GradeReview,
    InspectRepository,
    ListOpenAttempts,
    OfferReview,
    OpenWorkbench,
    ResumeAttempt,
    RevealHint,
    RevealSolutionFile,
    ReviewQueue,
    RunScenarioCommand,
    StartAttempt,
    SubmitScenario,
    SubmitSolution,
    SummariseProgress,
)
from practice.config import content_root, database_path, workspace_root
from practice.domain.exercise import ExerciseKind
from practice.domain.scheduling import Sm2Scheduler

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.ports import (
        AttemptRepository,
        Clock,
        ContentRepository,
        EditorLauncher,
        Grader,
        IdGenerator,
        RepoQueryFactory,
        ReviewRepository,
        SandboxProvisioner,
        Scheduler,
    )

__all__ = ["Services", "build_services"]


@dataclass(frozen=True, slots=True)
class Services:
    """Every port, wired, plus the use cases built over them.

    The use cases are properties rather than fields so that constructing the
    services costs nothing and a caller that only needs the content repository
    does not build a grader. They are cheap to rebuild — a frozen dataclass of
    references — so there is nothing to cache.
    """

    content: ContentRepository
    attempts: AttemptRepository
    reviews: ReviewRepository
    provisioner: SandboxProvisioner
    graders: GraderRegistry
    clock: Clock
    ids: IdGenerator
    repo_query: RepoQueryFactory
    scheduler: Scheduler
    editor: EditorLauncher

    @property
    def start_attempt(self) -> StartAttempt:
        return StartAttempt(
            content=self.content,
            attempts=self.attempts,
            provisioner=self.provisioner,
            graders=self.graders,
            clock=self.clock,
            ids=self.ids,
        )

    @property
    def submit_solution(self) -> SubmitSolution:
        return SubmitSolution(
            content=self.content,
            attempts=self.attempts,
            provisioner=self.provisioner,
            graders=self.graders,
            clock=self.clock,
        )

    @property
    def run_scenario_command(self) -> RunScenarioCommand:
        """No grader registry: running a command does not grade anything.

        Worth noticing rather than tidying into symmetry. It is the one use case
        that neither needs a grader nor completes an attempt, which is also why it
        is the only one that can be called twenty times in a row.
        """
        return RunScenarioCommand(
            content=self.content,
            attempts=self.attempts,
            provisioner=self.provisioner,
            clock=self.clock,
        )

    @property
    def submit_scenario(self) -> SubmitScenario:
        return SubmitScenario(
            content=self.content,
            attempts=self.attempts,
            provisioner=self.provisioner,
            graders=self.graders,
            clock=self.clock,
        )

    # --- the lifecycle ----------------------------------------------------

    @property
    def list_open_attempts(self) -> ListOpenAttempts:
        return ListOpenAttempts(
            content=self.content,
            attempts=self.attempts,
            provisioner=self.provisioner,
        )

    @property
    def resume_attempt(self) -> ResumeAttempt:
        """No clock: resuming is a read, and nothing about the attempt changes."""
        return ResumeAttempt(
            content=self.content,
            attempts=self.attempts,
            provisioner=self.provisioner,
        )

    @property
    def open_workbench(self) -> OpenWorkbench:
        """No clock and no graders: loading a page for display changes nothing.

        The same three ports as `resume_attempt`, which is the honest signal that
        the two are near neighbours -- they differ in what they do with a *finished*
        attempt, not in what they need to find one.
        """
        return OpenWorkbench(
            content=self.content,
            attempts=self.attempts,
            provisioner=self.provisioner,
        )

    @property
    def inspect_repository(self) -> InspectRepository:
        """No clock and no graders, like `open_workbench`: this only reads.

        The `repo_query` factory is the one port here that no other use case
        holds, and the reason it is on `Services` at all: it is the thing the
        grader and the panel have to share for the two of them to agree.
        """
        return InspectRepository(
            content=self.content,
            attempts=self.attempts,
            provisioner=self.provisioner,
            repo_query=self.repo_query,
        )

    @property
    def reveal_hint(self) -> RevealHint:
        """No provisioner: a hint is content and a log entry, and touches neither
        the sandbox nor the repository. It is the one use case that still works
        for an attempt whose workspace has been collected.
        """
        return RevealHint(
            content=self.content, attempts=self.attempts, clock=self.clock
        )

    @property
    def reveal_solution_file(self) -> RevealSolutionFile:
        """No clock and no graders: writing the handoff records nothing and
        grades nothing. The `EditorLauncher` has exactly one caller, which is
        the point — one place decides how this machine opens a file, and it is
        not a route handler.
        """
        return RevealSolutionFile(
            content=self.content,
            attempts=self.attempts,
            provisioner=self.provisioner,
            editor=self.editor,
        )

    @property
    def abandon_attempt(self) -> AbandonAttempt:
        return AbandonAttempt(
            content=self.content,
            attempts=self.attempts,
            provisioner=self.provisioner,
            clock=self.clock,
        )

    # --- scheduling -------------------------------------------------------

    @property
    def offer_review(self) -> OfferReview:
        """No scheduler and no clock: reading what a grade *would* be moves
        nothing, and the suggestion is computed from the attempt's own frozen
        elapsed time rather than from the current moment.
        """
        return OfferReview(
            content=self.content, attempts=self.attempts, reviews=self.reviews
        )

    @property
    def grade_review(self) -> GradeReview:
        """The only use case holding the `Scheduler`, and the only one that writes
        a card. Both halves of that sentence are the point: the port has exactly
        one caller, which is what keeps swapping SM-2 for FSRS a change here.
        """
        return GradeReview(
            content=self.content,
            attempts=self.attempts,
            reviews=self.reviews,
            scheduler=self.scheduler,
            clock=self.clock,
        )

    @property
    def review_queue(self) -> ReviewQueue:
        """No attempt store: what is due is a question about cards and the
        library, and an attempt is neither. The join that *does* need attempts is
        the progress summary.
        """
        return ReviewQueue(content=self.content, reviews=self.reviews, clock=self.clock)

    @property
    def summarise_progress(self) -> SummariseProgress:
        """The only read that touches both stores and the library at once -- and
        the only one holding the attempt repository for something other than
        finding one attempt by id.
        """
        return SummariseProgress(
            content=self.content,
            attempts=self.attempts,
            reviews=self.reviews,
            clock=self.clock,
        )

    @property
    def collect_workspaces(self) -> CollectWorkspaces:
        """No content repository: whether a directory is garbage is a question
        about the attempt table and the workspace root, and the exercise library
        has no part in it.
        """
        return CollectWorkspaces(attempts=self.attempts, provisioner=self.provisioner)


def build_services(
    *,
    content: Path | None = None,
    workspaces: Path | None = None,
    database: Path | None = None,
    clock: Clock | None = None,
    attempts: AttemptRepository | None = None,
) -> Services:
    """Build the real object graph.

    Nothing here *writes* to the disk, and as of Phase 6 that claim covers a
    database as well as a cache directory: `Database` stores a path and connects
    on first use, so building the graph for `practice validate` — which never
    reads a row — leaves nothing behind on a machine that has never run an
    attempt. `test_building_the_graph_writes_nothing_to_disk` is that claim.

    One read does happen: `PytestKataRunner` loads the plugin source that ships
    beside it, so a package missing that file fails here with a message about a
    missing file rather than three minutes later in the middle of grading.

    `attempts` overrides the store outright rather than the path, which is the
    escape hatch for a caller that wants no database at all — an application test
    driving the real use cases over the in-memory store. The path override is for
    a caller that wants a *disposable* one.
    """
    library = content if content is not None else content_root()
    storage = Database(database if database is not None else database_path())
    return Services(
        content=FilesystemContentRepository(library),
        attempts=(
            attempts if attempts is not None else SqliteAttemptRepository(storage)
        ),
        reviews=SqliteReviewRepository(storage),
        provisioner=SubprocessSandboxProvisioner(
            content_root=library,
            workspace_root=workspaces if workspaces is not None else workspace_root(),
            clock=clock,
        ),
        graders=build_graders(GitRepoQuery),
        clock=clock if clock is not None else SystemClock(),
        ids=Uuid4IdGenerator(),
        repo_query=GitRepoQuery,
        scheduler=Sm2Scheduler(),
        editor=SubprocessEditorLauncher(),
    )


def build_graders(query_for: RepoQueryFactory | None = None) -> GraderRegistry:
    """One grader per exercise kind, and as of Phase 5 that is both of them.

    Each is constructed with its own collaborator rather than reaching for one:
    `KataGrader` takes the pytest runner, `ScenarioGrader` takes the `RepoQuery`
    factory. That is what keeps both unit-testable against a double -- and what
    makes this function the only place that decides which real collaborator each
    one gets.

    **`query_for` is passed in as of Phase 8 rather than left to the grader's own
    default**, because the repo state panel became a second caller of that factory
    and `Services` now holds it. Two places naming `GitRepoQuery` would be two
    places to change, and the one that matters is the one where the grader and the
    panel could come to read the repository differently -- which is the single
    failure `InspectRepository` exists to make impossible. `None` still means the
    grader's default, which is what keeps `build_graders()` usable from a test that
    has no opinion about it.
    """
    graders: dict[ExerciseKind, Grader] = {
        ExerciseKind.KATA: KataGrader(PytestKataRunner()),
        ExerciseKind.GIT_SCENARIO: ScenarioGrader(query_for),
    }
    return GraderRegistry(graders=graders)
