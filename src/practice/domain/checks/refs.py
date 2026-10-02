"""Refs, ancestry, and the shape of history. Ten of the 22 assertions.

The family that does the actual discriminating. PLAN.md §6.6's central finding is
that `content-restored` passes for a revert, a `reset --hard` *and* a forgotten
push — the trees are byte-identical in all three — so what tells a right answer
from a wrong one is almost always in here: where a ref points, and what is
reachable from it.

Every one of these is a pure function of a `RepoQuery` and the author's
parameters. None of them shells out, none of them touches a path, and all of them
answer `passed: False` with a readable `actual` where a revision does not resolve
rather than raising (§6.5).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.checks.evaluation import (
    MISSING,
    CheckResult,
    CheckSpecError,
    compare,
    describe,
    matcher,
    resolve,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from practice.domain.checks.evaluation import CheckContext
    from practice.domain.ids import Sha

__all__ = [
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
]


def ref_points_at(context: CheckContext) -> CheckResult:
    """`ref_points_at {ref, target}` — the two resolve to the same commit.

    The assertion `fix-published` is built from, and the one that catches a local
    fix nobody can pull: `origin/main` has to point at the same commit `HEAD` does.
    """
    ref = context.params.text("ref")
    target = context.params.text("target")
    found = resolve(context.query, ref)
    wanted = resolve(context.query, target)
    return CheckResult(
        passed=found is not None and found == wanted,
        expected=f"{ref} at {target} ({describe(wanted)})",
        actual=f"{ref} at {describe(found)}",
    )


def is_ancestor(context: CheckContext) -> CheckResult:
    """`is_ancestor {ancestor, descendant}` — one is reachable from the other.

    The most important assertion in the vocabulary. It is what makes
    `history-preserved` possible — a `revert` leaves the bad commit reachable and a
    `reset --hard` does not, while both produce the same tree — and what makes
    `originals-recovered` possible, where a cherry-pick produces identical files
    as a commit that is not the one that was lost.

    Reflexive, because git is: `git merge-base --is-ancestor X X` exits 0. That
    matters rather than being a curiosity — on a solution that reverted and did not
    push, `@c3` and `HEAD` are the same commit, and an assertion that called that
    false would fail a correct answer.
    """
    ancestor_rev = context.params.text("ancestor")
    descendant_rev = context.params.text("descendant")
    ancestor = resolve(context.query, ancestor_rev)
    descendant = resolve(context.query, descendant_rev)
    if ancestor is None or descendant is None:
        return CheckResult(
            passed=False,
            expected=f"{ancestor_rev} reachable from {descendant_rev}",
            actual=_missing(
                {ancestor_rev: ancestor, descendant_rev: descendant},
            ),
        )
    reachable = context.query.is_ancestor(ancestor, descendant)
    return CheckResult(
        passed=reachable,
        expected=f"{ancestor_rev} ({ancestor.short}) reachable from "
        f"{descendant_rev} ({descendant.short})",
        actual="reachable" if reachable else "not reachable",
    )


def branch_exists(context: CheckContext) -> CheckResult:
    """`branch_exists {name}` — a branch of that name is present.

    Short names are accepted and resolved under `refs/heads/`, because that is how
    an author thinks about a branch. Keyed on the full name underneath, so a
    repository holding both a branch and a tag called `release` answers this and
    `tag_exists` differently — which it should.
    """
    return _ref_present(context, prefix="refs/heads/", kind="branch")


def tag_exists(context: CheckContext) -> CheckResult:
    """`tag_exists {name}` — a tag of that name is present."""
    return _ref_present(context, prefix="refs/tags/", kind="tag")


def tag_points_at(context: CheckContext) -> CheckResult:
    """`tag_points_at {name, target}` — the tag is on that commit.

    Separate from `ref_points_at` so an author can write `{name: v1.0}` rather
    than `{ref: refs/tags/v1.0}`, and so an annotated tag is peeled to the commit
    it names — the tag object's own hash is a different hash, and comparing it
    against `HEAD` would fail every correct answer.
    """
    name = context.params.text("name")
    target = context.params.text("target")
    full = _qualify(name, prefix="refs/tags/")
    found = resolve(context.query, full)
    wanted = resolve(context.query, target)
    return CheckResult(
        passed=found is not None and found == wanted,
        expected=f"tag {name} at {target} ({describe(wanted)})",
        actual=f"tag {name} at {describe(found)}",
    )


def head_detached(context: CheckContext) -> CheckResult:
    """`head_detached` — HEAD is not attached to any branch.

    The assertion that forced `RepoQuery.head_ref` to exist. No comparison of
    hashes can answer it: a detached HEAD sitting exactly on a branch tip is still
    detached, and that is the state `naive-detached-checkout.cmds` ends in.

    Almost always written with `not: true` — "you left the work on a branch" — which
    is the case that retired the paired-opposites design in §6.3, because
    `head_detached` was the one assertion with no partner to negate it.
    """
    attached = context.query.head_ref()
    return CheckResult(
        passed=attached is None,
        expected="a detached HEAD",
        actual="detached" if attached is None else f"attached to {attached}",
    )


def ref_unchanged(context: CheckContext) -> CheckResult:
    """`ref_unchanged {ref, since: fixture}` — the ref is where the fixture left it.

    What makes `main-untouched` expressible: recovery should not have collateral
    damage, and resetting `main` onto the feature work is a wrong answer that every
    other check in that exercise passes.

    `since:` has exactly one legal value today and is required anyway, rather than
    defaulted. The alternative value an author would reach for is "since the
    previous command", which is a different mechanism — it would need per-command
    snapshots, not the one the provisioner takes — so letting `since:` be optional
    now would make adding that a silent change in meaning for every existing check.
    """
    ref = context.params.text("ref")
    since = context.params.text("since")
    if since != "fixture":
        raise CheckSpecError(
            f"ref_unchanged: 'since' must be 'fixture', got {since!r}; nothing "
            f"else is recorded to compare against"
        )

    snapshot = context.query.snapshot()
    before = snapshot.get(ref)
    now = context.query.rev_parse(ref)
    return CheckResult(
        passed=before == now,
        expected=f"{ref} still at {describe(before)}",
        actual=f"{ref} at {describe(now)}",
    )


def commit_count(context: CheckContext) -> CheckResult:
    """`commit_count {ref, equals|at_least|at_most}` — how much history is reachable.

    Counts everything reachable, merges and both their sides included. A
    first-parent count would be a different and much less useful question: "how
    many commits are on this branch" is what an author means, and a merged side
    branch's commits are on it.
    """
    ref = context.params.text("ref", default="HEAD")
    operator, wanted = context.params.comparison()
    if resolve(context.query, ref) is None:
        return CheckResult(
            passed=False,
            expected=f"{ref} with {operator.replace('_', ' ')} {wanted} commits",
            actual=f"{ref} {MISSING}",
        )
    found = len(context.query.log(ref))
    return CheckResult(
        passed=compare(operator, found, wanted),
        expected=f"{ref} with {operator.replace('_', ' ')} {wanted} {_commits(wanted)}",
        actual=f"{found} {_commits(found)}",
    )


def commit_subject_matches(context: CheckContext) -> CheckResult:
    """`commit_subject_matches {ref, pattern}` — the message's first line matches.

    Deliberately about the *subject* and not the body. A commit message's first
    line is the part every git tool shows and the part a convention is about; an
    assertion over the whole message would be grading prose.
    """
    ref = context.params.text("ref", default="HEAD")
    pattern = matcher(context.params)
    subject = context.query.subject(ref)
    return CheckResult(
        passed=subject is not None and pattern.search(subject) is not None,
        expected=f"{ref} with a subject matching /{pattern.pattern}/",
        actual=MISSING if subject is None else repr(subject),
    )


def linear_history(context: CheckContext) -> CheckResult:
    """`linear_history {ref}` — nothing reachable from the ref is a merge.

    A parent count and nothing else. The message says nothing reliable about
    whether a commit was a merge, and neither does the author or the date — which
    is why `CommitInfo` carries `parents` at all.
    """
    ref = context.params.text("ref", default="HEAD")
    if resolve(context.query, ref) is None:
        return CheckResult(
            passed=False,
            expected=f"a linear history at {ref}",
            actual=f"{ref} {MISSING}",
        )
    merges = [commit for commit in context.query.log(ref) if commit.is_merge]
    return CheckResult(
        passed=not merges,
        expected=f"a linear history at {ref}",
        actual="linear"
        if not merges
        else f"{len(merges)} merge {_commits(len(merges))}: "
        + ", ".join(commit.sha.short for commit in merges),
    )


# --- shared pieces ---------------------------------------------------------


def _ref_present(context: CheckContext, *, prefix: str, kind: str) -> CheckResult:
    """`branch_exists` and `tag_exists`, which differ only in the namespace."""
    name = context.params.text("name")
    full = _qualify(name, prefix=prefix)
    present = full in context.query.refs()
    return CheckResult(
        passed=present,
        expected=f"a {kind} named {name}",
        actual=f"{full} at {describe(context.query.refs().get(full))}"
        if present
        else f"no {kind} {name}",
    )


def _qualify(name: str, *, prefix: str) -> str:
    """A full ref name, from either a short name or an already-full one.

    A name that is already fully qualified is left alone even when it is in a
    different namespace, so `tag_exists {name: refs/heads/main}` reports honestly
    about `refs/heads/main` rather than inventing `refs/tags/refs/heads/main`. An
    author who wrote that made a mistake, and the failure naming the ref they typed
    is the one that shows them which.
    """
    return name if name.startswith("refs/") else f"{prefix}{name}"


def _missing(candidates: Mapping[str, Sha | None]) -> str:
    """Name which of several revisions did not resolve.

    Which one is the whole content of the failure: "one of these two does not
    exist" sends a solver looking at both.
    """
    absent = [rev for rev, sha in candidates.items() if sha is None]
    return f"{', '.join(absent)} {MISSING}"


def _commits(count: int) -> str:
    return "commit" if count == 1 else "commits"
