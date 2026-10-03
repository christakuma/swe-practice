"""Check specs become check reports, and check reports become a verdict.

Satisfies `practice.domain.ports.Grader` structurally, like every adapter here
(ADR 0002), and sits where `KataGrader` sits for the other exercise kind — which is
the point of the kind registry in PLAN.md §3. Four decisions in it are worth more
than the code.

**Every check runs, including the ones after the first failure.** A grader that
stopped early would be cheaper and would make the verdict useless: the whole
argument of §6.6 is that a wrong answer passes some checks and fails others, and
*which* ones is the feedback. `naive-reset-force` passing `content-restored` and
failing `history-preserved` is the lesson; "failed at check 3" is not.

**The order is the exercise's.** Reports come back in the order the author declared
their checks, so two runs of the same answer read the same way down the page and an
author can put the thing they most want read first.

**It builds one `RepoQuery` per grading pass.** The query caches, so six checks
asking `status()` between them cost one `git` process rather than six, and the
instance not outliving the pass is what makes that safe — nothing runs a command
between two assertions. The factory is a callable rather than a `RepoQuery` argument
because `Grader.grade` is handed a `Workspace`, and because that is what lets the
assembly be unit-tested against `FakeRepoQuery` with no git and no filesystem.
`RepoQueryFactory` is a port in `domain/ports.py` as of Phase 8, when the repo
state panel became its second caller; it was declared here while this was the only
module that needed it, and a protocol in an adapter is reachable only by that
adapter's own collaborators.

**It refuses an exercise of the wrong kind rather than grading it badly.** The kind
registry should have refused first; this is the second gate, for the same reason
`SubprocessWorkspace` re-checks the command policy its caller already applied.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.adapters.git.repo_query import GitRepoQuery
from practice.domain.checks import registry
from practice.domain.exercise import GitScenarioSpec
from practice.domain.verdict import Verdict

if TYPE_CHECKING:
    from practice.domain.attempt import Attempt
    from practice.domain.exercise import Exercise
    from practice.domain.ports import RepoQueryFactory, Workspace

__all__ = ["ScenarioGrader", "ScenarioGraderError"]


class ScenarioGraderError(Exception):
    """The grader was handed something it cannot grade.

    A programming error rather than a solver mistake — the kind registry dispatches
    by `ExerciseKind` and should never have routed a kata here — so it is an
    exception and not a failing check. Making it a check would put "this tool is
    wired up wrong" in a verdict the solver has no way to act on.
    """


class ScenarioGrader:
    """Satisfies `practice.domain.ports.Grader` for `ExerciseKind.GIT_SCENARIO`."""

    __slots__ = ("_query_for",)

    def __init__(self, query_for: RepoQueryFactory | None = None) -> None:
        self._query_for: RepoQueryFactory = (
            query_for if query_for is not None else GitRepoQuery
        )

    def grade(
        self, exercise: Exercise, workspace: Workspace, attempt: Attempt
    ) -> Verdict:
        """Evaluate every check the exercise declares, in the order it declares them.

        `Verdict` refuses to be built empty, and `GitScenarioSpec` refuses to exist
        without at least one check — so there is no "no checks ran" case to handle
        here. That is two invariants doing one job, which is why neither has to be
        restated as a branch.
        """
        spec = exercise.spec
        if not isinstance(spec, GitScenarioSpec):
            raise ScenarioGraderError(
                f"{exercise.id} is a {exercise.kind.value}, which this grader "
                f"does not know how to grade"
            )

        query = self._query_for(workspace)
        return Verdict(
            reports=tuple(
                registry.evaluate(check, query, attempt) for check in spec.checks
            )
        )
