"""Shared machinery for the sandbox integration tests.

**These fixtures fail rather than skip when git or bash is missing**, and that
is a deliberate choice. A `pytest.mark.skipif` would be the conventional answer
and it is the wrong one here: the entire Phase 3 exit criterion is a claim about
what happens on two platforms, and a suite that quietly skips on one of them
reports success exactly as loudly as one that ran. The same reasoning as
`test_the_library_was_found` in the content suite (PLAN.md §9).

`ToolNotFoundError` already carries a message naming what to install, so the
failure is actionable rather than merely loud.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.content import FilesystemContentRepository
from practice.adapters.sandbox import (
    SubprocessSandboxProvisioner,
    SubprocessWorkspace,
    find_bash,
    find_git,
)
from practice.config import content_root
from practice.domain.exercise import GitScenarioSpec
from practice.domain.ids import AttemptId, ExerciseId

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from practice.domain.exercise import Exercise

#: The flagship scenario: three commits, the last one pushed (PLAN.md §6.6).
#: Used wherever a test needs a real repository rather than a specific one.
FLAGSHIP = ExerciseId("git/revert-a-pushed-commit")

#: The recovery scenario, whose whole premise is commits no ref points at.
RECOVERY = ExerciseId("git/recover-a-lost-commit")


@pytest.fixture(scope="session")
def tools() -> tuple[Path, Path]:
    """Resolve git and bash once, failing loudly and early if either is absent."""
    return find_git(), find_bash()


@pytest.fixture(scope="session")
def library() -> FilesystemContentRepository:
    """The real content library. These tests provision from real exercises.

    Deliberately not a synthetic fixture library: the thing being tested is that
    the two scenarios actually shipped can be provisioned and solved, and a
    hand-built two-commit repository would prove that about itself only.
    """
    return FilesystemContentRepository(content_root())


@pytest.fixture
def provisioner(
    tools: tuple[Path, Path], tmp_path: Path
) -> SubprocessSandboxProvisioner:
    """A provisioner rooted in a temp directory, never the user cache.

    A suite that provisioned into the real workspace root would collide with a
    session the developer has open, and `practice gc` would then report test
    leftovers as if they were real attempts.
    """
    del tools  # requested so the failure happens here, not mid-test
    return SubprocessSandboxProvisioner(
        content_root=content_root(), workspace_root=tmp_path / "ws"
    )


@pytest.fixture
def attempt_id() -> AttemptId:
    return AttemptId.parse("3f2a1b0c-0000-4000-8000-000000000001")


def scenario(library: FilesystemContentRepository, exercise_id: ExerciseId) -> Exercise:
    """One git scenario from the real library, with its kind asserted."""
    exercise = library.get(exercise_id)
    assert exercise is not None, f"{exercise_id} is missing from the library"
    assert isinstance(exercise.spec, GitScenarioSpec)
    return exercise


@pytest.fixture
def flagship(library: FilesystemContentRepository) -> Exercise:
    return scenario(library, FLAGSHIP)


@pytest.fixture
def workspace(
    provisioner: SubprocessSandboxProvisioner,
    flagship: Exercise,
    attempt_id: AttemptId,
) -> Iterator[SubprocessWorkspace]:
    """A provisioned workspace for the flagship scenario, disposed afterwards.

    Disposal is in the teardown rather than at the end of each test so that a
    failing test still cleans up — and so that disposal itself is exercised
    dozens of times on Windows, where it is the operation most likely to break.
    """
    provisioned = provisioner.provision(flagship, attempt_id)
    try:
        yield provisioned
    finally:
        provisioned.dispose()
