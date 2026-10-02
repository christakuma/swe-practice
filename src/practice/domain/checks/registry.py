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
   22 chances to get it wrong, and the one that got it wrong would report a
   failure as a pass.
2. **The author's words.** `CheckReport.from_spec` carries the label, the severity
   and the explanation across, so no assertion can forget to and none has to know
   how.
3. **A broken exercise failing cleanly.** `CheckSpecError` becomes a failing report
   naming the exercise's own bug, for the reason §6.5 gives about a missing ref: a
   traceback in the verdict panel teaches nothing, and the person reading it cannot
   fix the exercise. CI can, and the graded replay in the content suite is where
   that condition becomes a build failure.

**Two of these are on probation.** `reflog_contains` has turned out to be either
vacuously true (the fixture put the entry there) or a way of grading *how* the
solver got somewhere, which is the thing PLAN.md §1 exists to reject.
`command_count` actively fights the recovery scenario: an efficiency budget counts
read-only commands, so it penalises exactly the inspection that the
`used-the-reflog` advisory rewards. Both stay for now, both are flagged, and per
the §13 rule about abstractions earning their keep, both get deleted rather than
carried if no Phase 11 exercise needs them.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from practice.domain.checks import recovery, refs, trees, worktree
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
    "UNPROVEN_ASSERTIONS",
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
    "reflog_contains": recovery.reflog_contains,
    "stash_count": recovery.stash_count,
}

#: Assertions whose name is legal and whose function has not landed yet. A
#: within-phase scaffold, not a design: it exists so that each commit of Phase 5
#: stands alone and is green, while the schema keeps rejecting a typo against the
#: *whole* vocabulary rather than against however much of it is implemented. It is
#: empty by the end of the phase and this constant goes with it.
_PENDING: Final[Mapping[str, str]] = MappingProxyType(
    {
        "command_count": "process assertions land next",
        "command_used": "process assertions land next",
    }
)

#: Name to function, for everything that can be evaluated today.
CHECKS: Final[Mapping[str, CheckFunction]] = MappingProxyType(
    {
        **_REFS_AND_SHAPE,
        **_TREES_AND_CONTENT,
        **_WORKTREE_AND_INDEX,
        **_RECOVERY,
    }
)

#: Read the `Attempt` event log rather than the repository, which is why the
#: aggregate keeps every command instead of just a final state (PLAN.md §4.3).
#: Advisory by convention: they grade craft, not correctness.
PROCESS_ASSERTIONS: Final = frozenset({"command_count", "command_used"})

#: Every legal value of an `assert:` key — the table plus whatever is still
#: pending. The union rather than the table, so the schema rejects a typo against
#: the vocabulary the plan describes and not against this phase's progress.
ASSERTIONS: Final = frozenset(CHECKS) | frozenset(_PENDING)

#: Everything that interrogates the repository through `RepoQuery`.
CONTENT_ASSERTIONS: Final = ASSERTIONS - PROCESS_ASSERTIONS

#: Registered, unproven, and deleted rather than carried if Phase 11 does not
#: find an honest use for them. Named here rather than left as a comment so the
#: decision is greppable when that review comes round.
UNPROVEN_ASSERTIONS: Final = frozenset({"command_count", "reflog_contains"})


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

    Three things can go wrong and all three produce a failing report rather than an
    exception, because the reader of a verdict is a solver:

    * the assertion is registered but not yet dispatchable (a Phase 5 scaffold);
    * the `with:` mapping cannot be evaluated as written, which is an authoring bug
      that CI's graded replay turns into a build failure;
    * the repository is in a state the check did not expect, which is not an error
      at all — it is the failure the check exists to report (§6.5).

    A fourth thing cannot go wrong: an unregistered name never reaches here,
    because the content schema refuses to build a `CheckSpec` holding one.
    """
    function = CHECKS.get(spec.assertion)
    if function is None:
        return CheckReport.from_spec(
            spec,
            passed=False,
            expected=f"the {spec.assertion} assertion",
            actual=f"<not implemented yet: {_pending_reason(spec.assertion)}>",
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


def _pending_reason(name: str) -> str:
    return _PENDING.get(name, "no function is registered for it")
