"""The registry proper: `name -> CheckFunction`, and the one place `not:` is applied.

Phase 2 shipped this module as a **set of legal names** and said why: an exercise
naming an assertion that does not exist is a correctness hole rather than a style
problem — the check can never run, so the exercise passes with one fewer constraint
than its author wrote — and catching that needs nothing but the names, which were
knowable a phase before the functions were. Phase 5 makes it the table it was
always going to be. `is_registered` and `suggest` work unchanged, which is what the
schema in `adapters/content/` depends on.

**`evaluate` is the only place three things happen**, and that is the whole reason
it exists rather than each function doing its own:

1. **Negation.** PLAN.md §6.3 made `not:` a uniform modifier on every assertion
   instead of a set of paired opposites. A function that built its own report
   would have to invert its own verdict *and* rewrite its own `expected` string —
   20 chances to get it wrong, and the one that got it wrong would report a
   failure as a pass.
2. **The author's words.** `CheckReport.from_spec` carries the label, the severity
   and the explanation across, so no assertion can forget to and none has to know
   how.
3. **A broken exercise failing cleanly.** `CheckSpecError` becomes a failing report
   naming the exercise's own bug, for the reason §6.5 gives about a missing ref: a
   traceback in the verdict panel teaches nothing, and the person reading it cannot
   fix the exercise. CI can, and the graded replay in the content suite is where
   that condition becomes a build failure.

**Two entries were deleted in Phase 11, which is the point of having flagged
them.** `reflog_contains` and `command_count` shipped registered, implemented and
labelled unproven, with a note that they would go rather than be carried if no
Phase 11 exercise wanted them (§13). Twenty-four git scenarios later, none did —
`reflog_contains` is vacuously true wherever the fixture created the entry, and a
`command_count` budget counts the read-only commands that operational git is
mostly made of. So the vocabulary is twenty assertions rather than twenty-two,
and `UNPROVEN_ASSERTIONS` is gone with them. The reasoning for each sits in its
own module, where someone proposing to add it back will read it.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from practice.domain.checks import process, recovery, refs, trees, worktree
from practice.domain.checks.evaluation import CheckContext, CheckSpecError, Params
from practice.domain.verdict import CheckReport

if TYPE_CHECKING:
    from collections.abc import Mapping

    from practice.domain.attempt import Attempt
    from practice.domain.checks.evaluation import CheckFunction
    from practice.domain.exercise import CheckSpec
    from practice.domain.ports import RepoQuery

__all__ = [
    "ASSERTIONS",
    "CHECKS",
    "CONTENT_ASSERTIONS",
    "PROCESS_ASSERTIONS",
    "evaluate",
    "is_registered",
    "suggest",
]

#: Refs, ancestry, and the shape of history.
_REFS_AND_SHAPE: Final[Mapping[str, CheckFunction]] = {
    "branch_exists": refs.branch_exists,
    "commit_count": refs.commit_count,
    "commit_subject_matches": refs.commit_subject_matches,
    "head_detached": refs.head_detached,
    "is_ancestor": refs.is_ancestor,
    "linear_history": refs.linear_history,
    "ref_points_at": refs.ref_points_at,
    "ref_unchanged": refs.ref_unchanged,
    "tag_exists": refs.tag_exists,
    "tag_points_at": refs.tag_points_at,
}

#: Committed trees and file content.
_TREES_AND_CONTENT: Final[Mapping[str, CheckFunction]] = {
    "file_at_ref_matches": trees.file_at_ref_matches,
    "file_exists": trees.file_exists,
    "file_matches": trees.file_matches,
    "no_conflict_markers": trees.no_conflict_markers,
    "tree_equals": trees.tree_equals,
}

#: The working tree and the index.
_WORKTREE_AND_INDEX: Final[Mapping[str, CheckFunction]] = {
    "index_staged": worktree.index_staged,
    "unmerged_paths_empty": worktree.unmerged_paths_empty,
    "worktree_clean": worktree.worktree_clean,
}

#: Where git keeps the things you thought you had destroyed.
_RECOVERY: Final[Mapping[str, CheckFunction]] = {
    "stash_count": recovery.stash_count,
}

#: Reads the `Attempt` event log rather than the repository, which is why the
#: aggregate keeps every command instead of just a final state (PLAN.md §4.3).
#: Advisory by convention: it grades craft, not correctness. A family of one
#: since Phase 11, and still a family — `PROCESS_ASSERTIONS` is what tells
#: `CONTENT_ASSERTIONS` which names do not need a repository.
_PROCESS: Final[Mapping[str, CheckFunction]] = {
    "command_used": process.command_used,
}

#: Name to function: the whole vocabulary, grouped by what each family reads.
CHECKS: Final[Mapping[str, CheckFunction]] = MappingProxyType(
    {
        **_REFS_AND_SHAPE,
        **_TREES_AND_CONTENT,
        **_WORKTREE_AND_INDEX,
        **_RECOVERY,
        **_PROCESS,
    }
)

PROCESS_ASSERTIONS: Final = frozenset(_PROCESS)

#: Every legal value of an `assert:` key, which is now exactly what can be
#: dispatched. The two were briefly different while Phase 5 landed the functions a
#: family at a time, so that each commit stood alone while the schema kept
#: rejecting a typo against the *whole* vocabulary. That scaffold is gone.
ASSERTIONS: Final = frozenset(CHECKS)

#: Everything that interrogates the repository through `RepoQuery`.
CONTENT_ASSERTIONS: Final = ASSERTIONS - PROCESS_ASSERTIONS


#: Jaccard trigram overlap below which a candidate is noise rather than a
#: suggestion. Measured against the real vocabulary rather than guessed: genuine
#: typos score 0.33 (`equals_tree`) to 0.77 (`tree_equal`), while the best an
#: unrelated word manages is 0.11 (`revert` against `ref_unchanged`). Anywhere in
#: the gap works; 0.2 sits in the middle of it. A suggestion list that fires on
#: everything trains the reader to ignore it, which is worse than no list.
_SUGGESTION_THRESHOLD: Final = 0.2


def is_registered(name: str) -> bool:
    """Whether `name` is a legal `assert:` value."""
    return name in ASSERTIONS


def evaluate(spec: CheckSpec, query: RepoQuery, attempt: Attempt) -> CheckReport:
    """Run one check and report it in the author's words.

    Two things can go wrong and both produce a failing report rather than an
    exception, because the reader of a verdict is a solver:

    * the `with:` mapping cannot be evaluated as written, which is an authoring bug
      that CI's graded replay turns into a build failure;
    * the repository is in a state the check did not expect, which is not an error
      at all — it is the failure the check exists to report (§6.5).

    A third cannot: an unregistered name never reaches here, because the content
    schema refuses to build a `CheckSpec` holding one. The guard below is for the
    one way that could still happen — a name added to `ASSERTIONS` without a
    function — and it reports rather than raising for the same reason as the rest.
    """
    function = CHECKS.get(spec.assertion)
    if function is None:  # pragma: no cover - the schema rejects the name first
        return CheckReport.from_spec(
            spec,
            passed=False,
            expected=f"the {spec.assertion} assertion",
            actual="<no function is registered for it>",
        )

    context = CheckContext(
        query=query,
        attempt=attempt,
        params=Params(assertion=spec.assertion, values=spec.params),
    )
    try:
        result = function(context)
    except CheckSpecError as exc:
        return CheckReport.from_spec(
            spec,
            passed=False,
            expected=f"a usable {spec.assertion} check",
            actual=f"<this exercise is misconfigured: {exc}>",
        )

    if spec.negated:
        result = result.negate()
    return CheckReport.from_spec(
        spec,
        passed=result.passed,
        expected=result.expected,
        actual=result.actual,
    )


def suggest(name: str, *, limit: int = 3) -> tuple[str, ...]:
    """Registered names close enough to `name` to be worth offering.

    A validation error that says `unknown assertion 'tree_equal'` is correct and
    unhelpful; one that adds `did you mean tree_equals?` ends the problem at the
    error message. Matching is on shared character trigrams rather than edit
    distance so that a wrong word order — `equals_tree` — still finds its target,
    which plain Levenshtein does not.
    """

    def trigrams(value: str) -> frozenset[str]:
        padded = f"  {value} "
        return frozenset(padded[i : i + 3] for i in range(len(padded) - 2))

    # No guard for an empty `name`: padding means it still yields one trigram,
    # which matches nothing above the threshold, so the empty case falls out of
    # the normal path. Coverage caught the guard as dead before this shipped.
    target = trigrams(name)
    scored = []
    for candidate in ASSERTIONS:
        other = trigrams(candidate)
        overlap = len(target & other) / len(target | other)
        if overlap >= _SUGGESTION_THRESHOLD:
            scored.append((-overlap, candidate))

    return tuple(candidate for _, candidate in sorted(scored)[:limit])
