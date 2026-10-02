"""Trees and content. Four of the 22 assertions.

The family that answers "is the right thing in the file", and the one PLAN.md §6.6
warns hardest about: **content assertions alone cannot grade a git exercise.**
`content-restored` passes for a correct revert, for a `reset --hard` that rewrote
published history, and for a fix nobody pushed. The trees are byte-identical in
all three. What these assertions are for is the other half of the sentence — the
content *has* to be right too, and `tree_equals` says so without caring how.

**Where each one reads from, because it is the only thing that distinguishes
them.** `tree_equals` and `file_at_ref_matches` read *committed* content:
`tree_equals` compares a whole tree hash, which is how it notices a difference the
author never thought to write a pattern for. `file_exists` and `file_matches` read
the *working tree*, which is where a solver's half-finished work lives — and the
only state a merge-conflict exercise ever ends in (§15).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Final

from practice.domain.checks.evaluation import (
    MISSING,
    CheckResult,
    describe,
    matcher,
    resolve,
)

if TYPE_CHECKING:
    from practice.domain.checks.evaluation import CheckContext
    from practice.domain.ids import Sha

__all__ = [
    "CONFLICT_MARKERS",
    "file_at_ref_matches",
    "file_exists",
    "file_matches",
    "no_conflict_markers",
    "tree_equals",
]

#: What git leaves in a file it could not merge. Anchored to the start of a line,
#: and seven characters exactly, because that is what git writes — a shorter
#: pattern would match the `====` in a reStructuredText heading.
CONFLICT_MARKERS: Final = re.compile(r"^(<{7}|={7}|>{7})(\s|$)", re.MULTILINE)

#: How much of a file's content a failure report shows. Enough to recognise the
#: line, short enough that a verdict panel stays readable.
_EXCERPT: Final = 60


def tree_equals(context: CheckContext) -> CheckResult:
    """`tree_equals {ref, target}` — the two commits have identical content.

    A tree hash covers the whole tree recursively, so this is an exact statement
    about every file at once, and it needs no list of paths from the author. That
    is what makes it the right assertion for `content-restored`: "the build works
    again" is a claim about content the author should not have to enumerate.

    Note what it deliberately does *not* say: nothing about which commit, which
    branch, or how the content got there. A revert and a `reset --hard` both pass
    it. `is_ancestor` is what tells them apart.
    """
    ref = context.params.text("ref", default="HEAD")
    target = context.params.text("target")
    found = _tree(context, ref)
    wanted = _tree(context, target)
    return CheckResult(
        passed=found is not None and found == wanted,
        expected=f"the tree of {ref} identical to {target} ({describe(wanted)})",
        actual=f"{ref} has tree {describe(found)}",
    )


def file_exists(context: CheckContext) -> CheckResult:
    """`file_exists {path}` — the file is in the working tree.

    The working tree, not a commit, which is the whole point of it: an untracked
    file a solver just wrote is one git knows nothing about, and `file_exists` is
    how an exercise asks whether they wrote it.

    Often written with `not: true`, for an exercise whose answer is removing
    something.
    """
    path = context.params.text("path")
    content = context.query.worktree_file(path)
    return CheckResult(
        passed=content is not None,
        expected=f"a file at {path}",
        actual=f"{path} {MISSING}" if content is None else f"{path} is present",
    )


def file_matches(context: CheckContext) -> CheckResult:
    """`file_matches {path, pattern}` — the working tree's copy matches.

    Unanchored, like every pattern in this vocabulary: an author who wants to
    assert about the whole file writes `^` and `$` themselves.
    """
    path = context.params.text("path")
    pattern = matcher(context.params)
    content = context.query.worktree_file(path)
    return _matched(path, content, pattern, where="the working tree")


def file_at_ref_matches(context: CheckContext) -> CheckResult:
    """`file_at_ref_matches {ref, path, pattern}` — the *committed* copy matches.

    The committed/working-tree distinction is the reason this is a separate
    assertion rather than a parameter on `file_matches`. "You fixed it" and "you
    committed the fix" are different claims, and an exercise about a half-finished
    fix needs to be able to make one and not the other.
    """
    ref = context.params.text("ref", default="HEAD")
    path = context.params.text("path")
    pattern = matcher(context.params)
    return _matched(path, _blob(context, ref, path), pattern, where=ref)


def no_conflict_markers(context: CheckContext) -> CheckResult:
    """`no_conflict_markers {paths, ref?}` — no `<<<<<<<` left in those files.

    Paths are required rather than discovered, and that is the honest shape:
    `RepoQuery` has no directory listing, and inventing one would mean deciding
    what a check does about `.git/`, about untracked files, and about a repository
    with ten thousand paths. An author naming the files an exercise is about costs
    one line and says what they meant.

    Reads the working tree by default and a commit when `ref:` is given. The
    default is the useful one: a conflict that has been committed is a worse
    mistake, and a conflict that has not been resolved yet is the common one.

    A path that is not there counts as clean. Not a loophole — `file_exists` is the
    assertion for "the file is present", and reporting a missing file as full of
    conflict markers would be a lie about a different problem.
    """
    paths = context.params.paths("paths")
    ref = context.params.optional_text("ref")
    offenders = []
    for path in paths:
        content = (
            context.query.worktree_file(path)
            if ref is None
            else _blob(context, ref, path)
        )
        if content is not None and CONFLICT_MARKERS.search(content) is not None:
            offenders.append(path)
    where = "the working tree" if ref is None else ref
    return CheckResult(
        passed=not offenders,
        expected=f"no conflict markers in {', '.join(paths)} ({where})",
        actual="clean" if not offenders else f"markers in {', '.join(offenders)}",
    )


# --- shared pieces ---------------------------------------------------------


def _tree(context: CheckContext, rev: str) -> Sha | None:
    """A tree hash, with aliases resolved first.

    `resolve` before `tree_sha` rather than passing the raw string, because
    `tree_sha("@c2")` would hand `@c2` to git, which has never heard of it. The
    alias map is ours and is read before git sees anything (§6.5).
    """
    sha = resolve(context.query, rev)
    if sha is None:
        return None
    return context.query.tree_sha(sha.value)


def _blob(context: CheckContext, rev: str, path: str) -> str | None:
    """A committed file as text, decoded leniently.

    `errors="replace"` rather than refusing: a solver can commit any bytes they
    like, and a `UnicodeDecodeError` from inside a grading pass is the traceback
    §6.5 exists to prevent. Undecodable bytes become replacement characters, which
    no author's pattern matches by accident.
    """
    sha = resolve(context.query, rev)
    if sha is None:
        return None
    blob = context.query.read_blob(sha.value, path)
    return None if blob is None else blob.decode("utf-8", errors="replace")


def _matched(
    path: str, content: str | None, pattern: re.Pattern[str], *, where: str
) -> CheckResult:
    """One report shape for the two pattern-matching assertions."""
    if content is None:
        return CheckResult(
            passed=False,
            expected=f"{path} in {where} matching /{pattern.pattern}/",
            actual=f"{path} {MISSING} in {where}",
        )
    found = pattern.search(content)
    return CheckResult(
        passed=found is not None,
        expected=f"{path} in {where} matching /{pattern.pattern}/",
        actual=f"matched {found.group(0)[:_EXCERPT]!r}"
        if found is not None
        else f"no match in {len(content)} characters",
    )
