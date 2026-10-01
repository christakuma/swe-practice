"""The gate between a typed line and a running process.

Two jobs, and neither is security. The solver authored the content and owns the
machine (PLAN.md §8.1), so this is a correctness and blast-radius boundary:

1. **Parsing.** `shlex.split` into an argv, rejecting shell metacharacters —
   done by `practice.domain.commands`, not reimplemented here. That matters more
   than it looks: §5.3's guarantee is that the rules a reference solution is
   validated against in CI are byte-for-byte the rules a solver's input is
   executed against. Two implementations would let a scenario ship whose
   `solution.cmds` passes validation and cannot be typed.
2. **The allowlist.** Each exercise declares the commands it permits, and the
   allowlist comes from `AttemptPolicy.for_exercise` rather than being read off
   the spec again — same reason. One source, three readers.

**Rejection is an exception, not a result.** A disallowed command did not run,
so it is not a command run: giving it an exit code would put a fiction in the
attempt's event log, and `Attempt.record_command` is right to refuse it. The use
case catches this and shows the message.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.domain.attempt import AttemptPolicy
from practice.domain.commands import parse_command_line
from practice.domain.errors import InvalidValueError

if TYPE_CHECKING:
    from collections.abc import Sequence

    from practice.domain.exercise import Exercise, GitScenarioSpec

__all__ = ["CommandPolicy", "CommandRejectedError"]


class CommandRejectedError(Exception):
    """A command was refused before anything ran.

    Carries the line as typed so the caller can echo it back. A rejection the
    solver cannot connect to what they typed is a rejection they will make
    again.
    """

    def __init__(self, typed: str, reason: str) -> None:
        self.typed = typed
        self.reason = reason
        super().__init__(f"{typed!r}: {reason}")


@dataclass(frozen=True, slots=True)
class CommandPolicy:
    """What this exercise lets the solver type."""

    allowed: frozenset[str]

    @classmethod
    def for_exercise(cls, exercise: Exercise) -> CommandPolicy:
        """The allowlist the exercise declares, via the domain's own policy.

        Going through `AttemptPolicy` rather than reading `spec.allowed_commands`
        directly is what keeps a kata's empty allowlist from being a special
        case here: the domain already decided that a kata permits no commands,
        and restating it would be a second chance to get it wrong.
        """
        return cls(allowed=AttemptPolicy.for_exercise(exercise).allowed_commands)

    @classmethod
    def for_spec(cls, spec: GitScenarioSpec) -> CommandPolicy:
        """The allowlist straight off a scenario spec, for content tooling.

        `practice fixtures` and the content suite hold a spec without an
        `Exercise` around it often enough to be worth the three lines.
        """
        return cls(allowed=spec.allowed_commands)

    def vet_line(self, line: str) -> tuple[str, ...]:
        """Parse a typed line and check it, or explain the refusal.

        The two failures read differently on purpose. A metacharacter is a
        misunderstanding about what the console is — `echo x > f` would silently
        not redirect — so the message names the virtual commands that do the
        job. A disallowed program is a scope decision by the exercise author, so
        the message lists what *is* allowed.
        """
        try:
            argv = parse_command_line(line)
        except InvalidValueError as exc:
            raise CommandRejectedError(line, str(exc)) from exc
        self.vet(argv)
        return argv

    def vet(self, argv: Sequence[str]) -> None:
        """Check an already-parsed argv against the allowlist."""
        if not argv:
            raise CommandRejectedError("", "is not a command")
        program = argv[0]
        if program not in self.allowed:
            raise CommandRejectedError(
                " ".join(argv),
                f"{program!r} is not allowed by this exercise; allowed: {self.listing}",
            )

    @property
    def listing(self) -> str:
        """The allowlist as a human reads it, for an error message."""
        return ", ".join(sorted(self.allowed)) or "(none)"
