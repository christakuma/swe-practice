"""The assertion that reads the attempt, not the repository.

This is the only family that does not touch `RepoQuery` at all, and it is the
reason `Attempt` keeps a full event log rather than a final state (PLAN.md §4.3).
Everything else in the vocabulary asks "where did you end up". These ask "what did
you do", and the two questions have to be answered separately because the whole
point of §4.4's advisory severity is that you can get the right answer the wrong
way.

**Advisory by convention, not by construction.** Nothing here forces
`severity: advisory` — the author writes it, and `no-force-push` in the revert
scenario is advisory because its explanation says *you achieved the goal, and here
is the cost*. The convention is deliberate rather than enforced: a Phase 11 exercise
whose entire subject is a command might legitimately require one, and a domain that
refused would be legislating about content it has not seen.

**`command_count` was deleted here in Phase 11**, and the reasoning is worth
keeping because it is the §13 rule actually being applied rather than quoted. An
efficiency budget counts *read-only* commands, so on `recover-a-lost-commit` it
would have penalised exactly the inspection that the `used-the-reflog` advisory
rewards -- two checks pulling in opposite directions on one attempt. Making it
useful needs a `mutating_only: true` filter, which needs a maintained list of
read-only git subcommands, which is a list that is wrong the first time git adds
one. Twenty-four git scenarios were then written and not one of them wanted a
command budget, so it went.

What is left is one assertion, which is enough for the family to exist: `Attempt`
keeps its event log either way, and `command_used` is what turns it into a
verdict.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from practice.domain.checks.evaluation import CheckResult, matcher

if TYPE_CHECKING:
    from practice.domain.attempt import CommandRun
    from practice.domain.checks.evaluation import CheckContext

__all__ = ["command_used"]

#: How many matching command lines a report quotes. One is the useful number for a
#: pass — "you did this, here it is" — and the first match is the one that decided
#: the verdict.
_QUOTED: Final = 1


def command_used(context: CheckContext) -> CheckResult:
    """`command_used {pattern}` — some command the solver ran matches.

    The assertion that makes craft gradeable. In the revert scenario it appears
    twice and in opposite directions: `looked-before-leaping` rewards
    `^git (log|show|status|diff|reflog)\\b`, and `no-force-push` carries `not: true`
    over `push\\b.*--force`, flagging a force-push that happened to produce the right
    tree.

    Matched against `CommandRun.command_line`, which is `shlex.join` of the argv
    rather than the raw typed line. That normalisation is what makes a pattern
    writable: one space between arguments, whatever the solver typed.

    Unanchored, like every pattern in this vocabulary. The shipped checks rely on
    it — `push\\b.*(--force|-f)\\b` is meant to match anywhere in a line — and an
    author who wants anchoring writes `^`, as both shipped checks also do.
    """
    pattern = matcher(context.params)
    matched = [
        command
        for command in context.attempt.commands
        if pattern.search(command.command_line)
    ]
    return CheckResult(
        passed=bool(matched),
        expected=f"a command matching /{pattern.pattern}/",
        actual=_describe(matched, context.attempt.commands),
    )


def _describe(matched: list[CommandRun], all_commands: tuple[CommandRun, ...]) -> str:
    """The matching line, or how many were looked at and found nothing.

    The count matters on the failure: "no match in 0 commands" and "no match in 14
    commands" are different situations — the first is a solver who submitted without
    doing anything, which is worth saying out loud.
    """
    if matched:
        return ", ".join(repr(command.command_line) for command in matched[:_QUOTED])
    return f"no match in {len(all_commands)} {_commands(len(all_commands))}"


def _commands(count: int) -> str:
    return "command" if count == 1 else "commands"
