"""Real repositories for the `GitRepoQuery` and conformance suites.

Provisioned from the **real** content library rather than from a hand-built
two-commit repository, for the same reason the sandbox suite does it: what is
being tested is that the exercises actually shipped can be interrogated, and a
synthetic repository would only prove that about itself.

**These fixtures fail rather than skip when git or bash is missing.** A
`skipif` is the conventional answer and the wrong one here — a suite that
quietly skips reports success exactly as loudly as one that ran, and the claim
being made is cross-platform (PLAN.md §9).

A `replay` helper is here rather than in each test because every interesting
repository state in this suite is reached the same way: provision, then run a
list of commands through the real policy. That is also the only path a solver
has, so a test that reached a state another way would be testing a state the
product cannot produce.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.content import FilesystemContentRepository
from practice.adapters.git import GitRepoQuery
from practice.adapters.sandbox import (
    SubprocessSandboxProvisioner,
    SubprocessWorkspace,
    find_bash,
    find_git,
)
from practice.config import content_root
from practice.domain.commands import parse_command_list
from practice.domain.exercise import GitScenarioSpec
from practice.domain.ids import AttemptId, ExerciseId

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from practice.domain.exercise import Exercise

#: The flagship scenario: three commits, the last one pushed (PLAN.md §6.6).
FLAGSHIP = ExerciseId("git/revert-a-pushed-commit")

#: The recovery scenario, whose premise is commits no ref points at — so the
#: reflog, orphaned history and a detached HEAD are all reachable from it.
RECOVERY = ExerciseId("git/recover-a-lost-commit")

#: A long timeout: these run real git on a cold Windows filesystem.
TIMEOUT = 30.0


@pytest.fixture(scope="session")
def tools() -> tuple[Path, Path]:
    """Resolve git and bash once, failing loudly and early if either is absent."""
    return find_git(), find_bash()


@pytest.fixture(scope="session")
def content() -> FilesystemContentRepository:
    """The real exercise library."""
    return FilesystemContentRepository(content_root())


type Provision = Callable[[ExerciseId], SubprocessWorkspace]


@pytest.fixture
def provision(
    tools: tuple[Path, Path], content: FilesystemContentRepository, tmp_path: Path
) -> Iterator[Provision]:
    """A factory, because a test often needs the same scenario twice.

    Comparing a solved repository against a naive one means two workspaces, and
    sharing one would make what the second proves depend on what the first did.
    Each gets its own attempt id, so each gets its own directory.
    """
    del tools  # requested so a missing tool fails here, not mid-test
    provisioner = SubprocessSandboxProvisioner(
        content_root=content_root(), workspace_root=tmp_path / "ws"
    )
    provisioned: list[SubprocessWorkspace] = []

    def build(exercise_id: ExerciseId) -> SubprocessWorkspace:
        # The counter varies the first eight hex digits because those are what
        # `AttemptId.short` returns and therefore what names the directory.
        attempt_id = AttemptId.parse(
            f"{len(provisioned):08x}-0000-4000-8000-000000000000"
        )
        workspace = provisioner.provision(exercise(content, exercise_id), attempt_id)
        provisioned.append(workspace)
        return workspace

    try:
        yield build
    finally:
        for workspace in provisioned:
            workspace.dispose()


@pytest.fixture
def flagship(provision: Provision) -> SubprocessWorkspace:
    """The flagship scenario, straight out of its fixture."""
    return provision(FLAGSHIP)


@pytest.fixture
def recovery(provision: Provision) -> SubprocessWorkspace:
    """The recovery scenario, straight out of its fixture."""
    return provision(RECOVERY)


def exercise(content: FilesystemContentRepository, exercise_id: ExerciseId) -> Exercise:
    """One git scenario from the real library, with its kind asserted."""
    found = content.get(exercise_id)
    assert found is not None, f"{exercise_id} is missing from the library"
    assert isinstance(found.spec, GitScenarioSpec)
    return found


def query(workspace: SubprocessWorkspace) -> GitRepoQuery:
    """A `RepoQuery` over a workspace. One per grading pass, like the real thing."""
    return GitRepoQuery(workspace)


def replay(workspace: SubprocessWorkspace, commands: str) -> None:
    """Run a `.cmds`-shaped block through the real command policy.

    Through `run`, not `run_tool`: these are the commands a solver types, and a
    test that reached a state through the trusted channel would be testing a
    state no solver can produce (§8.1).

    A non-zero exit is not an error here. Some of these blocks are deliberately
    wrong, and being wrong sometimes means a command failing — what matters is
    that the policy allowed every line, which it enforces by raising.
    """
    for command in parse_command_list(commands):
        workspace.run(command.argv, timeout=TIMEOUT)


def replay_file(workspace: SubprocessWorkspace, path: Path) -> None:
    """Replay a real `.cmds` file out of the content library."""
    replay(workspace, path.read_text(encoding="utf-8"))


def scenario_dir(exercise_id: ExerciseId) -> Path:
    """Where an exercise's `.cmds` files live."""
    return content_root() / exercise_id.value
