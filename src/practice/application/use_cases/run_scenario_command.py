"""Run one command a solver typed, inside their attempt's workspace.

The use case `SubmitScenario` has nothing to grade without, and the only one in the
system that is called repeatedly within a single attempt. Four decisions in it.

**It parses, then lets the policy and the aggregate refuse.** The typed line becomes
an argv through `domain/commands.py`, the workspace's `CommandPolicy` vets it, and
`Attempt.record_command` refuses to remember a disallowed one. Three gates for one
rule, which is the deliberate duplication `Attempt` and `SubprocessWorkspace` both
document: the use case refuses to *offer* a disallowed command, the adapter refuses
to *execute* one, the aggregate refuses to *remember* one. A future code path that
forgets the gate gets a readable rejection rather than an exercise whose allowlist
quietly did not apply.

**The command runs before it is recorded**, because the record includes what it did.
The cost is the one failure this cannot make atomic: a process that runs and then
fails to be recorded has happened to the repository and not to the log. That is
unavoidable — the repository is the side effect — and it is why the budget is
checked *before* the process starts rather than relied on afterwards.

**The budget is checked here as well as in the aggregate.** `record_command` raises
when the budget is exhausted, which would mean running a 26th command and then
refusing to remember it: the repository would have moved under an attempt whose log
says it did not. So the limit is read before anything executes, and the aggregate's
check becomes the backstop it was always meant to be.

**A command that fails is a normal outcome, not an error.** `git revert` hitting a
conflict exits non-zero and is often the most instructive thing that happens in an
attempt. The result is returned with its exit code and its output, and only a
refusal — bad syntax, a disallowed program, an exhausted budget — raises.

**A finished attempt is refused here rather than three steps later.** Found by a
test: submission disposes of the workspace, so a stale browser tab sending one more
command reached `attach`, got nothing, and was told the workspace was gone and to
*abandon the attempt and start again* — about an attempt that had already been
graded. The aggregate would have refused too, with the right message, but only after
the command had run. One more instance of the duplication `Attempt` documents: the
use case refuses to *offer* what the aggregate refuses to *remember*.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import RanCommand
from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    WorkspaceGoneError,
)
from practice.domain.commands import parse_command_line
from practice.domain.errors import AttemptStateError, PolicyViolationError
from practice.domain.exercise import GitScenarioSpec

if TYPE_CHECKING:
    from practice.domain.ids import AttemptId
    from practice.domain.ports import (
        AttemptRepository,
        Clock,
        ContentRepository,
        SandboxProvisioner,
    )

__all__ = ["RunScenarioCommand"]


@dataclass(frozen=True, slots=True)
class RunScenarioCommand:
    """Execute one typed line against an attempt's repository and log it."""

    content: ContentRepository
    attempts: AttemptRepository
    provisioner: SandboxProvisioner
    clock: Clock

    def __call__(self, attempt_id: AttemptId, line: str) -> RanCommand:
        """Raises `InvalidValueError` for a line that is not a command at all.

        Which is also a `ValueError`, so a web layer can report it against the input
        field it came from without knowing anything about the domain (PLAN.md §4.1).
        """
        attempt = self.attempts.get(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(f"no attempt with id {attempt_id}")
        if not attempt.is_active:
            raise AttemptStateError(
                f"cannot run a command: attempt {attempt.id.short} is "
                f"{attempt.status.value}"
            )

        exercise = self.content.get(attempt.exercise_id)
        if exercise is None:
            raise ExerciseNotFoundError(
                f"attempt {attempt.id.short} is for {attempt.exercise_id}, which is "
                f"no longer in the library"
            )

        spec = exercise.spec
        if not isinstance(spec, GitScenarioSpec):
            raise ExerciseNotFoundError(
                f"{exercise.id} is a {exercise.kind.value} and has no command "
                f"console; katas are solved by submitting a solution"
            )

        # Before the process starts, not after: see the module docstring.
        if attempt.remaining_commands <= 0:
            raise PolicyViolationError(
                f"command budget exhausted: {attempt.policy.max_commands} commands"
            )

        argv = parse_command_line(line)

        workspace = self.provisioner.attach(exercise, attempt_id)
        if workspace is None:
            raise WorkspaceGoneError(
                f"the workspace for attempt {attempt.id.short} is no longer on "
                f"disk, so nothing can be run in it; abandon it and start again"
            )

        result = workspace.run(argv, timeout=spec.command_timeout_seconds)
        recorded = attempt.record_command(argv, result, at=self.clock.now())
        self.attempts.save(attempt)

        return RanCommand(attempt=attempt, exercise=exercise, command=recorded)
