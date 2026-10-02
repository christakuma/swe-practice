"""`RunScenarioCommand`: parse, vet, execute, record.

The only use case called repeatedly within one attempt, which makes its failure
modes different in kind from the others': the question is not "did it do the thing"
but "what does the attempt look like after it refused". Every refusal below is
checked for *both* halves — the exception, and the fact that the log did not move.
"""

from __future__ import annotations

import pytest

from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    WorkspaceGoneError,
)
from practice.domain.errors import (
    AttemptStateError,
    InvalidValueError,
    PolicyViolationError,
)
from practice.domain.ids import AttemptId, ExerciseId
from tests.unit.application.helpers import (
    a_run_scenario_command,
    a_start_attempt,
    a_submit_scenario,
    an_environment,
)

SCENARIO = ExerciseId("git/revert-a-pushed-commit")
KATA = ExerciseId("katas/two-sum")


def test_it_runs_the_command_and_records_it() -> None:
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)

    ran = a_run_scenario_command(world)(started.attempt.id, "git status --short")

    assert ran.command.argv == ("git", "status", "--short")
    assert ran.attempt.command_count == 1
    assert world.provisioner.workspace_for(started.attempt.id).commands == [
        ("git", "status", "--short")
    ]


def test_it_records_what_the_command_did_not_just_that_it_ran() -> None:
    """The result is part of the log, which is why the process runs before the
    record is appended -- and why `command_used` can read the log at grading time
    without re-running anything.
    """
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)

    ran = a_run_scenario_command(world)(started.attempt.id, "git status")

    assert ran.command.result.exit_code == 0
    assert ran.succeeded is True


def test_the_recorded_line_is_normalised() -> None:
    """`CommandRun.command_line` is `shlex.join` of the argv, so a pattern an author
    writes sees one space between arguments whatever the solver typed.
    """
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)

    ran = a_run_scenario_command(world)(started.attempt.id, "git   status    --short")

    assert ran.command.command_line == "git status --short"


def test_it_saves_the_attempt_after_every_command() -> None:
    """Not just at submission. An attempt that lost its last five commands because
    the process died would be an attempt whose repository and whose log disagree,
    and the log is the half that cannot be reconstructed.
    """
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)
    run = a_run_scenario_command(world)

    run(started.attempt.id, "git status")
    run(started.attempt.id, "git log --oneline")

    stored = world.attempts.get(started.attempt.id)
    assert stored is not None
    assert stored.command_count == 2


def test_it_reports_the_budget_so_a_console_can_redraw_itself() -> None:
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)

    ran = a_run_scenario_command(world)(started.attempt.id, "git status")

    assert ran.remaining_commands == 24


class TestRefusals:
    def test_a_line_that_is_not_a_command_is_refused_before_anything_runs(
        self,
    ) -> None:
        """`InvalidValueError` is also a `ValueError`, so a web layer can report it
        against the input field it came from without knowing the domain (§4.1).
        """
        world = an_environment()
        started = a_start_attempt(world)(SCENARIO)

        with pytest.raises(InvalidValueError, match="shell character"):
            a_run_scenario_command(world)(started.attempt.id, "echo broken > build.sh")

        assert world.provisioner.workspace_for(started.attempt.id).commands == []
        assert started.attempt.command_count == 0

    def test_a_program_the_exercise_does_not_allow_is_refused(self) -> None:
        """Three gates for one rule. The workspace's policy is what refuses here --
        the aggregate would too, which is the point: a path that forgot one still
        hits another.
        """
        world = an_environment()
        started = a_start_attempt(world)(SCENARIO)

        with pytest.raises(PolicyViolationError):
            a_run_scenario_command(world)(started.attempt.id, "curl example.com")

        assert started.attempt.command_count == 0

    def test_an_exhausted_budget_is_refused_before_the_process_starts(self) -> None:
        """The ordering that matters most here. `record_command` would raise too --
        after the command had already changed the repository, leaving an attempt
        whose log says something that did not happen.
        """
        world = an_environment()
        started = a_start_attempt(world)(SCENARIO)
        run = a_run_scenario_command(world)
        for _ in range(started.attempt.policy.max_commands):
            run(started.attempt.id, "git status")

        workspace = world.provisioner.workspace_for(started.attempt.id)
        before = len(workspace.commands)

        with pytest.raises(PolicyViolationError, match="budget exhausted"):
            run(started.attempt.id, "git status")

        assert len(workspace.commands) == before

    def test_an_attempt_that_does_not_exist_is_refused(self) -> None:
        world = an_environment()

        with pytest.raises(AttemptNotFoundError):
            a_run_scenario_command(world)(
                AttemptId.parse("00000000-0000-4000-8000-000000000999"), "git status"
            )

    def test_a_kata_has_no_command_console(self) -> None:
        """Not an oversight to paper over: a kata's allowlist is empty and its command
        budget is zero by design, so the honest answer names the other way in.
        """
        world = an_environment()
        started = a_start_attempt(world)(KATA)

        with pytest.raises(ExerciseNotFoundError, match="no command console"):
            a_run_scenario_command(world)(started.attempt.id, "git status")

    def test_a_library_that_changed_under_a_live_attempt_is_refused(self) -> None:
        world = an_environment()
        started = a_start_attempt(world)(SCENARIO)
        world.content.forget(SCENARIO)

        with pytest.raises(ExerciseNotFoundError, match="no longer in the library"):
            a_run_scenario_command(world)(started.attempt.id, "git status")

    def test_a_collected_workspace_is_refused_with_its_own_error(self) -> None:
        """Distinct from every other failure because the response is different: the
        attempt can be *abandoned* but never resumed, which is the whole reason
        PLAN.md §8.1 ties workspace lifetime to the ACTIVE status.
        """
        world = an_environment()
        started = a_start_attempt(world)(SCENARIO)
        world.provisioner.collect(started.attempt.id)

        with pytest.raises(WorkspaceGoneError, match="abandon it"):
            a_run_scenario_command(world)(started.attempt.id, "git status")

    def test_a_submitted_attempt_cannot_be_commanded_further(self) -> None:
        """Enforced by the aggregate rather than here, and worth a test at this level
        anyway: this is the use case a stale browser tab would call.
        """
        world = an_environment()
        started = a_start_attempt(world)(SCENARIO)
        a_submit_scenario(world)(started.attempt.id)

        with pytest.raises(AttemptStateError, match="completed"):
            a_run_scenario_command(world)(started.attempt.id, "git status")
