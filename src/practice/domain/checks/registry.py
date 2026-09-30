"""The names an `assert:` key may take, and nothing else yet.

**Why this exists before a single check function does.** An exercise file naming
an assertion that does not exist is a correctness hole, not a style problem: the
check can never run, so the exercise passes with one fewer constraint than its
author wrote. Catching it needs one thing only — the set of legal names — and
that set is knowable now, so the content schema in Phase 2 can reject a typo
instead of deferring it to a grading run in Phase 5 (PLAN.md §5.4).

**Why it is a set and not a dispatch table.** The obvious richer version maps each
name to its parameter contract, so `tree_equals` with a `rev:` key instead of
`ref:` also fails at validation time. That is worth having and is deliberately not
here: the contracts for two thirds of these assertions have never been written
down, and inventing them now would be designing the Phase 5 vocabulary from the
outside with no implementation to disagree with. When the functions land, this
module becomes the registry proper — `name -> CheckFunction` — and
`is_registered` keeps working unchanged.

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

from typing import Final

__all__ = [
    "ASSERTIONS",
    "CONTENT_ASSERTIONS",
    "PROCESS_ASSERTIONS",
    "UNPROVEN_ASSERTIONS",
    "is_registered",
    "suggest",
]

#: Refs, ancestry, and the shape of history.
_REFS_AND_SHAPE: Final = frozenset(
    {
        "branch_exists",
        "commit_count",
        "commit_subject_matches",
        "head_detached",
        "is_ancestor",
        "linear_history",
        "ref_points_at",
        "ref_unchanged",
        "tag_exists",
        "tag_points_at",
    }
)

#: Committed trees and file content.
_TREES_AND_CONTENT: Final = frozenset(
    {
        "file_at_ref_matches",
        "file_exists",
        "file_matches",
        "tree_equals",
    }
)

#: The working tree and the index.
_WORKTREE_AND_INDEX: Final = frozenset(
    {
        "index_staged",
        "no_conflict_markers",
        "unmerged_paths_empty",
        "worktree_clean",
    }
)

#: Where git keeps the things you thought you had destroyed.
_RECOVERY: Final = frozenset({"reflog_contains", "stash_count"})

#: Read the `Attempt` event log rather than the repository, which is why the
#: aggregate keeps every command instead of just a final state (PLAN.md §4.3).
#: Advisory by convention: they grade craft, not correctness.
PROCESS_ASSERTIONS: Final = frozenset({"command_count", "command_used"})

#: Everything that interrogates the repository through `RepoQuery`.
CONTENT_ASSERTIONS: Final = (
    _REFS_AND_SHAPE | _TREES_AND_CONTENT | _WORKTREE_AND_INDEX | _RECOVERY
)

#: Every legal value of an `assert:` key.
ASSERTIONS: Final = CONTENT_ASSERTIONS | PROCESS_ASSERTIONS

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
