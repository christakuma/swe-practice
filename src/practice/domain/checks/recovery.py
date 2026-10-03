"""Where git keeps the things you thought you had destroyed. One assertion.

The smallest family, and the one that lost a member. It shipped with two, and
`reflog_contains` was flagged on arrival as unproven: on `recover-a-lost-commit`
it is either vacuously true -- the fixture's own `reset --hard` put the entry
there, so every attempt passes it including the ones that never looked -- or it
is a way of grading *how* the solver got somewhere, which is the thing PLAN.md §1
exists to reject. `command_used` already rewards reaching for the reflog, over the
attempt log where that question belongs.

**Phase 11 deleted it.** Eight recovery scenarios were written, three of them
turning entirely on the reflog, and not one wanted to assert about its contents:
every one of them is graded on where the refs ended up. That is the §13 rule
applied rather than cited -- and the `RepoQuery.reflog` method went with it, since
nothing else had ever called it.

`stash_count` stays because `rescue-a-forgotten-stash` needs `{equals: 0}` to
tell `git stash apply` from `git stash pop`, which no other assertion can say.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.checks.evaluation import CheckResult, compare

if TYPE_CHECKING:
    from practice.domain.checks.evaluation import CheckContext

__all__ = ["stash_count"]


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


def _stashes(count: int) -> str:
    return "stash" if count == 1 else "stashes"
