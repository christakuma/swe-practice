"""`ExportTutorContext`: what a tutor is told, and what it is not.

Pure unit tests, over the same fakes `InspectRepository`'s are. Most of what
these pin down is an *absence*, which is the awkward kind of claim to test: that
the hints nobody revealed, the author's notes and the check list are not
anywhere in what comes back while an attempt is open.

So the boundary tests assert on `repr(context)` rather than field by field. A
frozen dataclass prints every field it has, including the nested ones, and a
test that looked only at the fields it expected a leak in would pass the day
somebody added a new one. `tests/content/test_tutor_context.py` then holds the
shipped library to the same thing through the renderer.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from practice.application.errors import AttemptNotFoundError, ExerciseNotFoundError
from practice.domain.attempt import (
    AttemptMode,
    AttemptStatus,
    CommandResult,
    CommandRun,
    HintRevealed,
)
from practice.domain.errors import PolicyViolationError
from practice.domain.exercise import ExerciseKind, Hint
from practice.domain.ids import AttemptId, ExerciseId
from tests.fakes import a_scenario
from tests.unit.application.helpers import (
    World,
    a_reveal_hint,
    a_run_scenario_command,
    a_start_attempt,
    a_submit_scenario,
    a_submit_solution,
    an_abandon_attempt,
    an_environment,
    an_export_tutor_context,
    an_inspect_repository,
)

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")

#: Three, so there is a difference between "revealed" and "left" to assert on.
HINTS = (
    Hint("Read `build.sh`, then `parser.py`."),
    Hint("Your teammate already has this commit. What happens to them?"),
    Hint("`git revert HEAD`, then push -- no force needed."),
)

#: The scenario fake's answer-shaped content, named so a test reads as the claim.
NOTES = "Why revert and not reset."
CHECK_LABEL = "The bad commit is still reachable."
CHECK_EXPLANATION = "Published history is not yours to rewrite."


def a_scenario_attempt(
    *, mode: AttemptMode = AttemptMode.PRACTICE
) -> tuple[World, AttemptId]:
    world = an_environment()
    world.content.replace_with(replace(a_scenario(), hints=HINTS))
    return world, a_start_attempt(world)(SCENARIO, mode=mode).attempt.id


def a_kata_attempt() -> tuple[World, AttemptId]:
    world = an_environment()
    return world, a_start_attempt(world)(KATA).attempt.id


# --- what it carries -------------------------------------------------------


def test_it_carries_the_exercise_as_the_solver_was_shown_it() -> None:
    world, attempt_id = a_scenario_attempt()

    context = an_export_tutor_context(world)(attempt_id)

    assert context.exercise_id == SCENARIO
    assert context.title == "Revert a pushed commit"
    assert context.kind is ExerciseKind.GIT_SCENARIO
    assert context.prompt == "Undo it without rewriting published history."
    assert context.status is AttemptStatus.ACTIVE
    assert context.mode is AttemptMode.PRACTICE
    assert not context.is_finished


def test_the_allowlist_comes_back_sorted_and_the_budget_as_what_is_left() -> None:
    """Sorted, because the policy holds a frozenset and a bundle whose allowlist
    reshuffled between two exports would look like something had changed.
    """
    world, attempt_id = a_scenario_attempt()
    a_run_scenario_command(world)(attempt_id, "git status")

    context = an_export_tutor_context(world)(attempt_id)

    assert context.allowed_commands == ("cat", "git")
    assert context.commands_left == 24


def test_commands_and_hints_come_back_in_the_order_they_happened() -> None:
    """One sequence, not two lists: a hint revealed before the command that fixed
    things and one revealed after it are different stories.
    """
    world, attempt_id = a_scenario_attempt()
    world.provisioner.workspace_for(attempt_id).result = CommandResult(
        exit_code=1, stderr="CONFLICT (content): Merge conflict in parser.py"
    )
    a_run_scenario_command(world)(attempt_id, "git revert HEAD")
    a_reveal_hint(world)(attempt_id)
    a_run_scenario_command(world)(attempt_id, "git status")

    context = an_export_tutor_context(world)(attempt_id)

    assert [type(event) for event in context.events] == [
        CommandRun,
        HintRevealed,
        CommandRun,
    ]
    first = context.events[0]
    assert isinstance(first, CommandRun)
    assert first.command_line == "git revert HEAD"
    assert first.result.exit_code == 1
    assert "CONFLICT" in first.result.stderr


def test_an_open_scenario_carries_the_repository_the_panel_shows() -> None:
    """Equal to `InspectRepository`'s answer, which is the reason `view_of` is
    shared: a tutor told the worktree is clean while the panel says otherwise
    is worse than a tutor told nothing.
    """
    world, attempt_id = a_scenario_attempt()
    first, second = world.repo.chain("skeleton", "bad refactor")
    world.repo.branch("main", second).remote("main", first)
    world.repo.status(unmerged=["parser.py"])

    context = an_export_tutor_context(world)(attempt_id)

    assert context.repo is not None
    assert context.repo == an_inspect_repository(world)(attempt_id)
    assert context.repo.status.unmerged == frozenset({"parser.py"})


# --- the boundary ----------------------------------------------------------


def test_a_hint_nobody_revealed_is_nowhere_in_it() -> None:
    world, attempt_id = a_scenario_attempt()
    a_reveal_hint(world)(attempt_id)

    context = an_export_tutor_context(world)(attempt_id)

    assert context.hints_left == 2
    assert HINTS[0].text in repr(context)
    assert HINTS[1].text not in repr(context)
    assert HINTS[2].text not in repr(context)


def test_an_open_attempt_carries_no_notes_and_no_checks() -> None:
    """The notes are the author's write-up and the check list names the answer,
    so either one mid-attempt is the solution with extra steps.
    """
    world, attempt_id = a_scenario_attempt()

    context = an_export_tutor_context(world)(attempt_id)

    assert context.notes is None
    assert context.verdict is None
    assert NOTES not in repr(context)
    assert CHECK_LABEL not in repr(context)
    assert CHECK_EXPLANATION not in repr(context)


def test_a_graded_attempt_gains_the_verdict_and_the_notes_together() -> None:
    """What is being asked for now is a post-mortem, and both are its material."""
    world, attempt_id = a_scenario_attempt()
    a_submit_scenario(world)(attempt_id)

    context = an_export_tutor_context(world)(attempt_id)

    assert context.is_finished
    assert context.verdict is not None
    assert context.notes == NOTES


def test_an_abandoned_attempt_gains_neither() -> None:
    """Nothing graded it and it is about to be retried, so the notes would be
    the answer to the next attempt rather than the explanation of this one.
    """
    world, attempt_id = a_scenario_attempt()
    an_abandon_attempt(world)(attempt_id)

    context = an_export_tutor_context(world)(attempt_id)

    assert context.status is AttemptStatus.ABANDONED
    assert context.verdict is None
    assert context.notes is None


# --- the repository, when there is not one ----------------------------------


def test_a_finished_scenario_has_no_repository() -> None:
    world, attempt_id = a_scenario_attempt()
    a_submit_scenario(world)(attempt_id)

    assert an_export_tutor_context(world)(attempt_id).repo is None


def test_an_open_attempt_whose_workspace_is_gone_is_still_answered() -> None:
    """Where `InspectRepository` raises. The history is in the database, not the
    workspace, and it is the larger half of what a tutor is asked about.
    """
    world, attempt_id = a_scenario_attempt()
    a_run_scenario_command(world)(attempt_id, "git status")
    world.provisioner.collect(attempt_id)

    context = an_export_tutor_context(world)(attempt_id)

    assert context.repo is None
    assert len(context.events) == 1


def test_a_kata_has_no_repository_and_no_console() -> None:
    world, attempt_id = a_kata_attempt()

    context = an_export_tutor_context(world)(attempt_id)

    assert context.repo is None
    assert context.allowed_commands == ()


# --- the solver's source ---------------------------------------------------


def test_a_scenario_has_no_source() -> None:
    world, attempt_id = a_scenario_attempt()

    context = an_export_tutor_context(world)(attempt_id)

    assert context.source is None
    assert context.language is None


def test_a_katas_source_is_read_from_the_workspace() -> None:
    world, attempt_id = a_kata_attempt()
    world.provisioner.workspace_for(attempt_id).write_file(
        "stub.py", "def two_sum(): ..."
    )

    context = an_export_tutor_context(world)(attempt_id)

    assert context.source == "def two_sum(): ..."
    assert context.language == "python"


def test_a_draft_the_caller_is_holding_beats_the_file() -> None:
    """The browser editor's contents exist nowhere else until they are
    submitted, so the file would be describing the stub.
    """
    world, attempt_id = a_kata_attempt()
    world.provisioner.workspace_for(attempt_id).write_file("stub.py", "the stub")

    context = an_export_tutor_context(world)(attempt_id, draft="half an answer")

    assert context.source == "half an answer"


def test_a_missing_file_is_no_source_rather_than_an_error() -> None:
    world, attempt_id = a_kata_attempt()

    assert an_export_tutor_context(world)(attempt_id).source is None


def test_a_kata_whose_workspace_is_gone_has_no_source() -> None:
    world, attempt_id = a_kata_attempt()
    world.provisioner.collect(attempt_id)

    assert an_export_tutor_context(world)(attempt_id).source is None


def test_a_graded_katas_source_is_the_one_that_was_graded() -> None:
    """Not the draft, even when one is offered: it would be describing a
    different answer from the one the verdict beside it is about.
    """
    world, attempt_id = a_kata_attempt()
    a_submit_solution(world)(attempt_id, "the submitted answer")

    context = an_export_tutor_context(world)(attempt_id, draft="something newer")

    assert context.source == "the submitted answer"
    # And once, not as an event as well: the log's `SolutionSaved` is where it
    # came from, and it is left out of `events` for that reason.
    assert context.events == ()


def test_an_abandoned_kata_that_saved_nothing_has_no_source() -> None:
    world, attempt_id = a_kata_attempt()
    an_abandon_attempt(world)(attempt_id)

    assert an_export_tutor_context(world)(attempt_id).source is None


# --- what it refuses -------------------------------------------------------


def test_an_open_interview_is_refused() -> None:
    world, attempt_id = a_scenario_attempt(mode=AttemptMode.INTERVIEW)

    with pytest.raises(PolicyViolationError, match="interview mode withholds"):
        an_export_tutor_context(world)(attempt_id)


def test_a_finished_interview_is_not() -> None:
    """The mode withdraws help *during* the attempt. Afterwards it is an attempt
    like any other, and picking it over is the point of having sat it.
    """
    world, attempt_id = a_scenario_attempt(mode=AttemptMode.INTERVIEW)
    a_submit_scenario(world)(attempt_id)

    context = an_export_tutor_context(world)(attempt_id)

    assert context.mode is AttemptMode.INTERVIEW
    assert context.verdict is not None


def test_an_unknown_attempt_is_refused() -> None:
    world = an_environment()

    with pytest.raises(AttemptNotFoundError, match="no attempt with id"):
        an_export_tutor_context(world)(
            AttemptId.parse("00000000-0000-4000-8000-000000000000")
        )


def test_an_exercise_that_left_the_library_is_refused() -> None:
    world, attempt_id = a_scenario_attempt()
    world.content.forget(SCENARIO)

    with pytest.raises(ExerciseNotFoundError, match="no longer in the library"):
        an_export_tutor_context(world)(attempt_id)


def test_exporting_records_nothing_on_the_attempt() -> None:
    """Asking a tutor is not recorded the way revealing a hint is (ADR 0023): the
    tool cannot know whether a copied bundle was ever pasted.
    """
    world, attempt_id = a_scenario_attempt()
    a_run_scenario_command(world)(attempt_id, "git status")
    before = world.attempts.get(attempt_id)
    assert before is not None
    events = before.events

    an_export_tutor_context(world)(attempt_id)
    an_export_tutor_context(world)(attempt_id)

    after = world.attempts.get(attempt_id)
    assert after is not None
    assert after.events == events
