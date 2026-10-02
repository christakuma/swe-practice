"""The two assertions that read the attempt, not the repository.

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

**One of the two is on probation, and this one fights an exercise.**
`command_count` is worse than merely unproven. An efficiency budget counts
*read-only* commands, so on `recover-a-lost-commit` it penalises exactly the
inspection that the `used-the-reflog` advisory rewards — the two checks would be
pulling in opposite directions on the same attempt. Making it useful needs a
`mutating_only: true` filter, which needs a maintained list of read-only git
subcommands, which is a list that is wrong the first time git adds one. Registered,
implemented, flagged, and deleted rather than carried if Phase 11 does not find a
use (§13).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from practice.domain.checks.evaluation import CheckResult, matcher

if TYPE_CHECKING:
    from practice.domain.attempt import CommandRun
    from practice.domain.checks.evaluation import CheckContext

__all__ = ["command_count", "command_used"]

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


def command_count(context: CheckContext) -> CheckResult:
    """`command_count {at_most}` — the solver stayed inside a budget.

    **Unproven, and actively harmful on the one exercise that could use it.** See
    the module docstring: the count includes read-only commands, so a budget
    punishes the inspection that operational git is mostly made of.

    `at_most` only. `equals` would be grading a solver for typing a specific number
    of commands, and `at_least` would be rewarding thrashing — neither is a thing an
    author means, so the general `comparison()` helper the counting assertions share
    is deliberately not used here.
    """
    wanted = context.params.integer("at_most")
    found = context.attempt.command_count
    return CheckResult(
        passed=found <= wanted,
        expected=f"at most {wanted} {_commands(wanted)}",
        actual=f"{found} {_commands(found)}",
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
