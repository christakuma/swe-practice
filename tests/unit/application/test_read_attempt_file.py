"""`ReadAttemptFile`: what a tutor may look at, and what it is refused.

Pure unit tests over the fakes. The caller this use case exists for is a model
choosing its own arguments, so the cases worth the most are the ones no solver
would type: the hidden suite asked for by name, and a revision that is really
an option to git. `tests/integration/test_mcp_server.py` runs that last one
against real git, which is the only place it can be shown to matter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    UnsupportedExerciseKindError,
    WorkspaceGoneError,
)
from practice.application.registry import GraderRegistry
from practice.application.use_cases import ReadAttemptFile
from practice.domain.attempt import AttemptMode
from practice.domain.errors import (
    AttemptStateError,
    InvalidValueError,
    PolicyViolationError,
)
from practice.domain.exercise import ExerciseKind
from practice.domain.ids import AttemptId, ExerciseId
from tests.fakes import a_drill
from tests.unit.application.helpers import (
    RecordingGrader,
    World,
    a_read_attempt_file,
    a_start_attempt,
    a_submit_scenario,
    an_environment,
)

if TYPE_CHECKING:
    from practice.domain.ids import Sha
    from practice.domain.ports import RepoQuery, Workspace
    from tests.fakes import FakeRepoQuery

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")
DRILL = ExerciseId("sql/one-row-per-customer")


def a_scenario_attempt(
    *, mode: AttemptMode = AttemptMode.PRACTICE
) -> tuple[World, AttemptId]:
    world = an_environment()
    return world, a_start_attempt(world)(SCENARIO, mode=mode).attempt.id


def a_kata_attempt() -> tuple[World, AttemptId]:
    world = an_environment()
    return world, a_start_attempt(world)(KATA).attempt.id


def a_drill_attempt() -> tuple[World, AttemptId]:
    """The shared environment registers two graders, and a drill needs a third
    before `StartAttempt` will open one.
    """
    world = an_environment()
    world.content.add(a_drill())
    graders = GraderRegistry(graders={ExerciseKind.SQL_DRILL: RecordingGrader()})
    return world, a_start_attempt(world, graders=graders)(DRILL).attempt.id


# --- a repository ----------------------------------------------------------


def test_it_reads_a_file_from_the_working_tree() -> None:
    """Uncommitted, which is the point: a conflict's markers are in the working
    tree and in no commit.
    """
    world, attempt_id = a_scenario_attempt()
    world.repo.working_file("parser.py", "<<<<<<< HEAD\ndef parse_line():\n")

    text = a_read_attempt_file(world)(attempt_id, "parser.py")

    assert text == "<<<<<<< HEAD\ndef parse_line():\n"


def test_a_file_that_is_not_there_is_none_rather_than_an_error() -> None:
    world, attempt_id = a_scenario_attempt()

    assert a_read_attempt_file(world)(attempt_id, "nope.py") is None


def test_it_reads_a_committed_file_at_a_revision() -> None:
    world, attempt_id = a_scenario_attempt()
    first = world.repo.commit("skeleton", files={"parser.py": "def parse_line():"})
    second = world.repo.commit(
        "bad refactor", parents=[first], files={"parser.py": "def parse():"}
    )
    world.repo.branch("main", second).head("refs/heads/main")
    read = a_read_attempt_file(world)

    assert read(attempt_id, "parser.py", rev="HEAD") == "def parse():"
    assert read(attempt_id, "parser.py", rev="HEAD~1") == "def parse_line():"


def test_a_revision_that_does_not_resolve_is_none() -> None:
    world, attempt_id = a_scenario_attempt()
    (only,) = world.repo.chain("one")
    world.repo.branch("main", only).head("refs/heads/main")

    assert a_read_attempt_file(world)(attempt_id, "parser.py", rev="HEAD~9") is None


def test_a_file_missing_at_that_revision_is_none() -> None:
    world, attempt_id = a_scenario_attempt()
    (only,) = world.repo.chain("one")
    world.repo.branch("main", only).head("refs/heads/main")

    assert a_read_attempt_file(world)(attempt_id, "nope.py", rev="HEAD") is None


def test_bytes_that_are_not_text_come_back_as_noise_rather_than_raising() -> None:
    """A solver can commit anything, and a tutor that asked to see it should be
    shown that it is not text rather than an exception.
    """
    world, attempt_id = a_scenario_attempt()
    (only,) = world.repo.chain("one")
    world.repo.blob(only, "logo.png", b"\xff\xfe\x00png")
    world.repo.branch("main", only).head("refs/heads/main")

    text = a_read_attempt_file(world)(attempt_id, "logo.png", rev="HEAD")

    assert text is not None
    assert "png" in text
    assert "�" in text


# --- a revision that is really an option ------------------------------------


@pytest.mark.parametrize("rev", ["--output=pwned.txt", "-p", "--"])
def test_a_revision_beginning_with_a_hyphen_is_refused(rev: str) -> None:
    """`git show --output=FILE` opens FILE for writing, so a revision chosen by
    a model could turn the read-only port into a write. Refused before anything
    is asked of the repository.
    """
    world, attempt_id = a_scenario_attempt()

    with pytest.raises(InvalidValueError, match="cannot begin with a hyphen"):
        a_read_attempt_file(world)(attempt_id, "parser.py", rev=rev)


class RecordingQuery:
    """Wraps a fake repository and remembers what `read_blob` was asked for.

    Everything else is forwarded, so it still answers like a repository; the
    one thing a test wants from it is the revision string that got through.
    """

    def __init__(self, inner: FakeRepoQuery) -> None:
        self._inner = inner
        self.blob_revisions: list[str] = []

    def rev_parse(self, rev: str) -> Sha | None:
        return self._inner.rev_parse(rev)

    def read_blob(self, rev: str, path: str) -> bytes | None:
        self.blob_revisions.append(rev)
        return self._inner.read_blob(rev, path)

    def __getattr__(self, name: str) -> object:
        return getattr(self._inner, name)


def test_what_reaches_the_repository_is_a_hash_and_never_the_callers_string() -> None:
    """The second guard, and the one that does not depend on spotting a hyphen:
    the revision is resolved first, so `read_blob` is handed forty hex
    characters whatever the caller wrote.
    """
    world, attempt_id = a_scenario_attempt()
    (only,) = world.repo.chain("one")
    world.repo.branch("main", only).head("refs/heads/main")
    recording = RecordingQuery(world.repo.build())

    def factory(workspace: Workspace) -> RepoQuery:
        del workspace
        return recording  # type: ignore[return-value]

    read = ReadAttemptFile(
        content=world.content,
        attempts=world.attempts,
        provisioner=world.provisioner,
        repo_query=factory,
    )
    read(attempt_id, "parser.py", rev="main")

    assert recording.blob_revisions == [only.value]


# --- a directory ------------------------------------------------------------


def test_a_katas_own_file_is_readable() -> None:
    world, attempt_id = a_kata_attempt()
    world.provisioner.workspace_for(attempt_id).write_file("stub.py", "def two_sum():")

    assert a_read_attempt_file(world)(attempt_id, "stub.py") == "def two_sum():"


def test_a_katas_hidden_suite_is_refused_by_name() -> None:
    """Refused, not reported missing: it is right there in the workspace, and
    "no such file" would be a lie a model could catch.
    """
    world, attempt_id = a_kata_attempt()
    world.provisioner.workspace_for(attempt_id).write_file("tests.py", "the suite")

    with pytest.raises(UnsupportedExerciseKindError, match=r"may read stub\.py"):
        a_read_attempt_file(world)(attempt_id, "tests.py")


@pytest.mark.parametrize("path", ["solution.py", "../tests.py", "./tests.py", ""])
def test_anything_else_in_a_katas_workspace_is_refused_too(path: str) -> None:
    """An allowlist of one, so there is no spelling of the suite's path to find."""
    world, attempt_id = a_kata_attempt()

    with pytest.raises(UnsupportedExerciseKindError):
        a_read_attempt_file(world)(attempt_id, path)


def test_a_kata_has_no_revisions() -> None:
    world, attempt_id = a_kata_attempt()

    with pytest.raises(UnsupportedExerciseKindError, match="no repository"):
        a_read_attempt_file(world)(attempt_id, "stub.py", rev="HEAD")


def test_a_katas_missing_file_is_none() -> None:
    world, attempt_id = a_kata_attempt()

    assert a_read_attempt_file(world)(attempt_id, "stub.py") is None


def test_a_drills_seed_is_readable_as_well_as_its_answer() -> None:
    """The schema is the question, and the solver is meant to read it."""
    world, attempt_id = a_drill_attempt()
    workspace = world.provisioner.workspace_for(attempt_id)
    workspace.write_file("seed.sql", "CREATE TABLE customers (id);")
    workspace.write_file("stub.sql", "SELECT 1;")
    read = a_read_attempt_file(world)

    assert read(attempt_id, "seed.sql") == "CREATE TABLE customers (id);"
    assert read(attempt_id, "stub.sql") == "SELECT 1;"


def test_a_drills_reference_is_refused() -> None:
    world, attempt_id = a_drill_attempt()

    with pytest.raises(UnsupportedExerciseKindError, match=r"stub\.sql and seed\.sql"):
        a_read_attempt_file(world)(attempt_id, "solution.sql")


# --- what it refuses -------------------------------------------------------


def test_a_finished_attempt_has_no_file_to_read() -> None:
    world, attempt_id = a_scenario_attempt()
    a_submit_scenario(world)(attempt_id)

    with pytest.raises(AttemptStateError, match="completed"):
        a_read_attempt_file(world)(attempt_id, "parser.py")


def test_an_open_interview_is_refused() -> None:
    world, attempt_id = a_scenario_attempt(mode=AttemptMode.INTERVIEW)

    with pytest.raises(PolicyViolationError, match="interview mode withholds"):
        a_read_attempt_file(world)(attempt_id, "parser.py")


def test_an_attempt_whose_workspace_is_gone_is_refused() -> None:
    world, attempt_id = a_scenario_attempt()
    world.provisioner.collect(attempt_id)

    with pytest.raises(WorkspaceGoneError, match="no file to read"):
        a_read_attempt_file(world)(attempt_id, "parser.py")


def test_an_unknown_attempt_is_refused() -> None:
    world = an_environment()

    with pytest.raises(AttemptNotFoundError, match="no attempt with id"):
        a_read_attempt_file(world)(
            AttemptId.parse("00000000-0000-4000-8000-000000000000"), "parser.py"
        )


def test_an_exercise_that_left_the_library_is_refused() -> None:
    world, attempt_id = a_scenario_attempt()
    world.content.forget(SCENARIO)

    with pytest.raises(ExerciseNotFoundError, match="no longer in the library"):
        a_read_attempt_file(world)(attempt_id, "parser.py")


def test_reading_records_nothing_on_the_attempt() -> None:
    world, attempt_id = a_scenario_attempt()
    world.repo.working_file("parser.py", "def parse():")

    a_read_attempt_file(world)(attempt_id, "parser.py")

    attempt = world.attempts.get(attempt_id)
    assert attempt is not None
    assert attempt.events == ()
    assert world.provisioner.workspace_for(attempt_id).commands == []
