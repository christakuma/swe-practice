"""Where git keeps the things you thought you had destroyed. Two assertions.

The smallest family and the one with the most to answer for: **one of its two
members is on probation.**

`reflog_contains` has not found an honest use in two exercises. On
`recover-a-lost-commit` it is either vacuously true — the fixture's own `reset
--hard` put the entry there, so every attempt passes it including the ones that
never looked — or it is a way of grading *how* the solver got somewhere, which is
the thing PLAN.md §1 exists to reject. `command_used` already rewards reaching for
the reflog, and does it over the attempt log where that question belongs.

It is implemented rather than left as a name, because a registered assertion with
no function is a correctness hole of the kind Phase 2's registry exists to close,
and because an implementation is what a Phase 11 author needs in order to discover
whether they want it. Per the §13 rule about abstractions earning their keep: **if
no Phase 11 exercise needs it, it gets deleted rather than carried.**
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.checks.evaluation import CheckResult, compare, matcher

if TYPE_CHECKING:
    from collections.abc import Sequence

    from practice.domain.checks.evaluation import CheckContext
    from practice.domain.ports import ReflogEntry

__all__ = ["reflog_contains", "stash_count"]

#: How many reflog messages a failure report lists before it stops. A reflog on a
#: busy repository runs to hundreds of entries, and a verdict panel that printed
#: them all would bury every other check.
_SHOWN = 5


def stash_count(context: CheckContext) -> CheckResult:
    """`stash_count {equals|at_least|at_most}` — how many stashes are left.

    Usually `{equals: 0}`: a stash is work in flight, and an exercise about
    finishing something wants it applied rather than parked. `git stash list` on a
    repository with no stash exits 0 and prints nothing, so zero is a real count
    here rather than a missing-ref case.
    """
    operator, wanted = context.params.comparison()
    found = len(context.query.stash_list())
    return CheckResult(
        passed=compare(operator, found, wanted),
        expected=f"{operator.replace('_', ' ')} {wanted} {_stashes(wanted)}",
        actual=f"{found} {_stashes(found)}",
    )


def reflog_contains(context: CheckContext) -> CheckResult:
    """`reflog_contains {ref, pattern}` — some position of `ref` has that message.

    **Unproven.** See the module docstring: it is vacuously true wherever the
    fixture created the entry, and grading *how* a solver arrived somewhere is what
    §1 rejects. Kept, flagged, and deleted rather than carried if Phase 11 does not
    find an honest use.

    Matches the message git shows after the colon in `git reflog`'s own output —
    `commit: add parser`, `reset: moving to HEAD~2` — because that is the string a
    pattern gets written against by someone reading a terminal.

    A ref with no reflog is a clean failure rather than an error: a branch created
    with `git branch` and never moved has an empty one, and that is an ordinary
    repository state rather than a fault (§6.5).
    """
    ref = context.params.text("ref", default="HEAD")
    pattern = matcher(context.params)
    entries = context.query.reflog(ref)
    matched = [entry for entry in entries if pattern.search(entry.message)]
    return CheckResult(
        passed=bool(matched),
        expected=f"a {ref} reflog entry matching /{pattern.pattern}/",
        actual=_describe(ref, entries, matched),
    )


def _describe(
    ref: str,
    entries: Sequence[ReflogEntry],
    matched: Sequence[ReflogEntry],
) -> str:
    """What was found, with enough of the reflog to see why it did not match.

    The position is reported as `HEAD@{3}` rather than as a hash, because that is
    the thing a solver can type -- and reading a reflog properly, past the top
    entry, is the whole lesson of the exercise this assertion belongs to.
    """
    if matched:
        first = matched[0]
        return f"{ref}@{{{first.index}}}: {first.message!r}"
    if not entries:
        return f"{ref} has no reflog"
    shown = ", ".join(repr(entry.message) for entry in entries[:_SHOWN])
    more = f" (+{len(entries) - _SHOWN} more)" if len(entries) > _SHOWN else ""
    return f"no match in {len(entries)} entries: {shown}{more}"


def _stashes(count: int) -> str:
    return "stash" if count == 1 else "stashes"
