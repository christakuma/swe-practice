"""A real kata workspace, provisioned from the real library.

Deliberately not a synthetic two-test kata: what these tests are about is that
`content/katas/two-sum` can actually be graded, and a hand-built kata would
prove that about itself only. The same reasoning as the sandbox suite's
`library` fixture.

These fixtures **fail rather than skip** when git is missing, for the reason
`tests/integration/sandbox/conftest.py` gives at length: a suite that quietly
skips reports success exactly as loudly as one that ran. Git is needed here even
though a kata has no repository, because the provisioner builds the same scoped
workspace for both kinds and that environment is derived from where git lives.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from practice.adapters.content import FilesystemContentRepository
from practice.adapters.kata import PytestKataRunner
from practice.adapters.sandbox import SubprocessSandboxProvisioner, find_git
from practice.config import content_root
from practice.domain.exercise import KataSpec
from practice.domain.ids import AttemptId, ExerciseId

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from practice.adapters.sandbox import SubprocessWorkspace
    from practice.domain.exercise import Exercise

#: The kata the library ships, and the one every assertion here is about.
TWO_SUM = ExerciseId("katas/two-sum")

type Provision = Callable[[], SubprocessWorkspace]


@pytest.fixture(scope="session")
def git() -> Path:
    """Resolve git once, failing loudly and early if it is absent."""
    return find_git()


@pytest.fixture(scope="session")
def library() -> FilesystemContentRepository:
    return FilesystemContentRepository(content_root())


@pytest.fixture
def kata(library: FilesystemContentRepository) -> Exercise:
    exercise = library.get(TWO_SUM)
    assert exercise is not None, f"{TWO_SUM} is missing from the library"
    assert isinstance(exercise.spec, KataSpec)
    return exercise


#: Long enough that no amount of load on the machine can breach it, which is
#: the point: it is a *wall-clock* budget on a subprocess.
#:
#: **Found by running the suite in parallel.** Every test on this fixture is
#: about what the runner reports — parsed records, docstring labels, ANSI
#: escapes, which config it obeyed — and none is about the limit; the one that
#: is has `kata_spec_with_a_short_limit`. They nonetheless inherited two-sum's
#: real ten seconds, and a run that normally takes about a second and a half
#: went over it under twelve-way oversubscription: pytest was killed, no report
#: was written, and the assertion failed as "no failures were reported", which
#: looks like a parsing bug and is not. A loaded CI runner could have done the
#: same thing at any point (PLAN.md §16).
_GENEROUS_LIMIT_SECONDS = 120


@pytest.fixture
def spec(kata: Exercise) -> KataSpec:
    """The real kata's spec, with the time limit lifted out of the way.

    `replace` rather than a different kata, so everything these tests are about
    — the files, the hidden suite, the complexity expectation — is the shipped
    exercise. Only the number that nothing here asserts on is changed.
    """
    assert isinstance(kata.spec, KataSpec)
    return replace(kata.spec, time_limit_seconds=_GENEROUS_LIMIT_SECONDS)


@pytest.fixture
def provision(git: Path, tmp_path: Path, kata: Exercise) -> Iterator[Provision]:
    """A factory: a test that grades twice needs two workspaces.

    Grading writes `solution.py` and a report into the workspace, so a second
    run in the same one starts from the first one's leftovers and what it proves
    depends on the order the tests happen to be declared in.
    """
    del git  # requested so a missing tool fails here, not mid-test
    provisioner = SubprocessSandboxProvisioner(
        content_root=content_root(), workspace_root=tmp_path / "ws"
    )
    provisioned: list[SubprocessWorkspace] = []

    def build() -> SubprocessWorkspace:
        workspace = provisioner.provision(
            kata,
            AttemptId.parse(f"{len(provisioned):08x}-0000-4000-8000-000000000000"),
        )
        provisioned.append(workspace)
        return workspace

    try:
        yield build
    finally:
        for workspace in provisioned:
            workspace.dispose()


@pytest.fixture
def workspace(provision: Provision) -> SubprocessWorkspace:
    return provision()


@pytest.fixture
def runner() -> PytestKataRunner:
    return PytestKataRunner()


@pytest.fixture
def reference(kata: Exercise, spec: KataSpec) -> str:
    """The exercise's own reference solution, read from the library.

    Never copied into a workspace by the provisioner — it is an answer key, and
    the only reason this suite can read it is that it is the grader's test, not
    the solver's.
    """
    return (content_root() / kata.id.value / spec.reference).read_text(encoding="utf-8")


@pytest.fixture
def stub(kata: Exercise, spec: KataSpec) -> str:
    return (content_root() / kata.id.value / spec.stub).read_text(encoding="utf-8")


@pytest.fixture
def kata_spec_with_a_short_limit(spec: KataSpec) -> KataSpec:
    """The same kata with a one-second time limit.

    `replace` rather than a second exercise file, so the spec under test is the
    real one in every respect but the number being exercised. Ten seconds of
    waiting to prove a timeout works is ten seconds on every CI run, twice.

    This is the only test in the file that is *about* the limit, which is what
    lets `spec` lift it for everything else.
    """
    return replace(spec, time_limit_seconds=1)
