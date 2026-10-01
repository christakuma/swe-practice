"""The single wiring point: the only module that imports across every layer.

Manual dependency injection, no framework, no decorators, no magic — you can
read the whole object graph in one file, which is the property PLAN.md §3 claims
and this file either keeps or breaks.

**Why it arrives now and not in Phase 0.** A wiring module with one adapter in
it is the abstraction §13 says to delete rather than carry, so Phase 2
deliberately did without one. Phase 4 is the first time there is a graph: a
content repository, a provisioner, an attempt store, a runner behind a grader
behind a registry, a clock and an id generator, assembled into two use cases.
Six objects with four edges between them is exactly when a reader benefits from
one place that shows the shape.

**`Services` holds ports, not implementations.** The annotations are the port
protocols, so mypy checks at the only place it can that each adapter still
satisfies the port it is being passed as — an adapter never subclasses its port
(ADR 0002), so nothing else would notice a drift. The attribute types being
protocols is also what lets a test build a `Services` out of fakes and drive the
real use cases with it.

The two `*_root` arguments exist because the test suite needs to point at a
disposable library and a disposable workspace root. Everything else comes from
`config`, which is the module that knows where things live on this machine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.adapters.clock import SystemClock
from practice.adapters.content import FilesystemContentRepository
from practice.adapters.ids import Uuid4IdGenerator
from practice.adapters.kata import KataGrader, PytestKataRunner
from practice.adapters.persistence import InMemoryAttemptRepository
from practice.adapters.sandbox import SubprocessSandboxProvisioner
from practice.application.registry import GraderRegistry
from practice.application.use_cases import StartAttempt, SubmitSolution
from practice.config import content_root, workspace_root
from practice.domain.exercise import ExerciseKind

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.ports import (
        AttemptRepository,
        Clock,
        ContentRepository,
        Grader,
        IdGenerator,
        SandboxProvisioner,
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
    provisioner: SandboxProvisioner
    graders: GraderRegistry
    clock: Clock
    ids: IdGenerator

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


def build_services(
    *,
    content: Path | None = None,
    workspaces: Path | None = None,
    clock: Clock | None = None,
    attempts: AttemptRepository | None = None,
) -> Services:
    """Build the real object graph.

    Nothing here *writes* to the disk: every adapter stores the paths it was
    given and reads them when it is used. That is deliberate — building the
    graph must not create a cache directory as a side effect, or `practice
    validate` would leave one behind on a machine that has never run an
    attempt.

    One read does happen: `PytestKataRunner` loads the plugin source that ships
    beside it, so a package missing that file fails here with a message about a
    missing file rather than three minutes later in the middle of grading.
    """
    library = content if content is not None else content_root()
    return Services(
        content=FilesystemContentRepository(library),
        attempts=attempts if attempts is not None else InMemoryAttemptRepository(),
        provisioner=SubprocessSandboxProvisioner(
            content_root=library,
            workspace_root=workspaces if workspaces is not None else workspace_root(),
            clock=clock,
        ),
        graders=build_graders(),
        clock=clock if clock is not None else SystemClock(),
        ids=Uuid4IdGenerator(),
    )


def build_graders() -> GraderRegistry:
    """One grader per exercise kind that has one.

    `ExerciseKind.GIT_SCENARIO` is absent rather than mapped to a stub, which is
    what makes the registry's refusal honest: a placeholder grader would be
    something an attempt could be completed against, and a kata-shaped verdict
    for a git scenario is worse than no verdict at all (Phase 5).
    """
    graders: dict[ExerciseKind, Grader] = {
        ExerciseKind.KATA: KataGrader(PytestKataRunner())
    }
    return GraderRegistry(graders=graders)
