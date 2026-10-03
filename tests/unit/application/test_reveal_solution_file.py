"""`RevealSolutionFile`: the handoff from the browser editor to the solver's own.

Four things this has to get right, and each one is a way the feature could be
quietly useless rather than broken:

* the path is the attempt's *own* file, in the attempt's *own* workspace;
* the handoff is written **before** the editor is launched, or the editor opens
  on the previous bytes;
* nothing is appended to the event log, because an editor save is not something
  the solver did in the exercise (Phase 8, PLAN.md §16);
* a launch that failed still comes back with the path on it.

The refusals are the same four `OpenWorkbench` has plus two of its own, and they
are tested here rather than left to the route, for the reason §9 gives: anything
assertable one layer down belongs one layer down.
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
from practice.application.use_cases import RevealSolutionFile
from practice.domain.errors import AttemptStateError
from practice.domain.ids import AttemptId, ExerciseId
from tests.unit.application.helpers import (
    a_reveal_solution_file,
    a_start_attempt,
    an_environment,
)

if TYPE_CHECKING:
    from pathlib import Path

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")

TYPED = "def two_sum(numbers, target):\n    return (0, 1)\n"


def test_it_hands_back_the_path_of_the_attempts_own_solution_file() -> None:
    world = an_environment()
    started = a_start_attempt(world)(KATA)

    revealed = a_reveal_solution_file(world)(started.attempt.id)

    workspace = world.provisioner.workspace_for(started.attempt.id)
    assert revealed.path == workspace.resolve("stub.py")
    assert revealed.name == "stub.py"


def test_it_opens_the_editor_on_that_file_and_nothing_else() -> None:
    world = an_environment()
    started = a_start_attempt(world)(KATA)

    revealed = a_reveal_solution_file(world)(started.attempt.id)

    assert world.editor.revealed == [revealed.path]
    assert revealed.launched
    assert revealed.detail is None


def test_the_handoff_is_written_into_the_file() -> None:
    """What was on screen when the button was pressed, or it is lost."""
    world = an_environment()
    started = a_start_attempt(world)(KATA)

    a_reveal_solution_file(world)(started.attempt.id, TYPED)

    workspace = world.provisioner.workspace_for(started.attempt.id)
    assert workspace.read_file("stub.py") == TYPED


def test_the_handoff_is_written_before_the_editor_is_launched() -> None:
    """An editor that opens on the previous bytes is a bug nobody reproduces.

    Asserted by reading the file *from inside* the launch, which is the only
    moment the ordering is observable -- afterwards both have happened and the
    end state cannot tell which came first.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    workspace = world.provisioner.workspace_for(started.attempt.id)
    seen: list[str] = []

    class Peeking:
        """An editor that reads the file it is handed, at the moment it is handed
        it. Satisfies `EditorLauncher` structurally, like the real one.
        """

        def reveal(self, path: Path) -> str | None:
            del path
            seen.append(workspace.read_file("stub.py"))
            return None

    RevealSolutionFile(
        content=world.content,
        attempts=world.attempts,
        provisioner=world.provisioner,
        editor=Peeking(),
    )(started.attempt.id, TYPED)

    assert seen == [TYPED]


def test_nothing_is_written_when_there_is_no_handoff_to_write() -> None:
    """A reveal with no source leaves the file as the solver left it.

    The CLI and a page reload both reach it that way, and overwriting a file
    somebody has been editing with an empty string would be the worst available
    answer to "show me my file".
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    workspace = world.provisioner.workspace_for(started.attempt.id)
    workspace.write_file("stub.py", TYPED)

    a_reveal_solution_file(world)(started.attempt.id)

    assert workspace.read_file("stub.py") == TYPED


def test_revealing_records_nothing_on_the_attempt() -> None:
    """The file is the state; the log is the story (PLAN.md §16, Phase 8)."""
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    before = len(started.attempt.events)

    a_reveal_solution_file(world)(started.attempt.id, TYPED)

    stored = world.attempts.get(started.attempt.id)
    assert stored is not None
    assert len(stored.events) == before


def test_an_editor_that_could_not_be_started_still_yields_the_path() -> None:
    """The feature is the file; the launch is the convenience on top of it."""
    world = an_environment()
    world.editor.problem = "'code' is not on this machine's PATH"
    started = a_start_attempt(world)(KATA)

    revealed = a_reveal_solution_file(world)(started.attempt.id, TYPED)

    assert not revealed.launched
    assert revealed.detail == "'code' is not on this machine's PATH"
    assert revealed.path.name == "stub.py"


def test_it_refuses_an_attempt_that_is_not_there() -> None:
    world = an_environment()

    with pytest.raises(AttemptNotFoundError):
        a_reveal_solution_file(world)(
            AttemptId.parse("00000000-0000-4000-8000-000000000000")
        )


def test_it_refuses_a_finished_attempt() -> None:
    """Submission disposes of the workspace, so there is no file to open."""
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    started.attempt.abandon(at=world.clock.now())
    world.attempts.save(started.attempt)

    with pytest.raises(AttemptStateError, match="abandoned"):
        a_reveal_solution_file(world)(started.attempt.id)


def test_it_refuses_an_exercise_that_left_the_library() -> None:
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.content.forget(KATA)

    with pytest.raises(ExerciseNotFoundError, match="abandon it"):
        a_reveal_solution_file(world)(started.attempt.id)


def test_it_refuses_a_git_scenario() -> None:
    """The mirror of `InspectRepository` refusing a kata: the question does not
    apply. A scenario is graded on the repository as it stands, and there is no
    one file to put in front of anybody.
    """
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)

    with pytest.raises(UnsupportedExerciseKindError, match="no solution file"):
        a_reveal_solution_file(world)(started.attempt.id)


def test_it_refuses_an_attempt_whose_workspace_has_been_collected() -> None:
    world = an_environment()
    started = a_start_attempt(world)(KATA)
    world.provisioner.collect(started.attempt.id)

    with pytest.raises(WorkspaceGoneError, match="no longer on disk"):
        a_reveal_solution_file(world)(started.attempt.id)


def test_a_scenario_is_refused_before_its_workspace_is_attached() -> None:
    """Order matters in the refusals, not just their presence.

    A kind that has no solution file has none whether or not its workspace is
    still there, so the message a solver gets must not depend on which happened
    first -- and the one that explains is the kind, not the disk.
    """
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)
    world.provisioner.collect(started.attempt.id)

    with pytest.raises(UnsupportedExerciseKindError):
        a_reveal_solution_file(world)(started.attempt.id)
