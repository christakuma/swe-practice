"""The working tree and the index. Three of the 20 assertions.

The family that asks whether a solver *finished*. A fix that only exists in a
working directory is not a fix, and a half-applied `git checkout <sha> -- .` looks
exactly like success until the next checkout throws it all away.

All four read `WorktreeStatus`, and the interesting decision is that they do not
each decide what "clean" means. `is_clean` and `is_pristine` live on the value
object in `domain/ports.py`, so both `RepoQuery` implementations answer the question
identically and the §6.5 rule about untracked files is written in one place instead
of being repeated here.

PLAN.md §6.3 files `no_conflict_markers` under this heading, and it is in `trees`
instead: it reads file content rather than status, so it shares `_blob` and the
working-tree read with `file_matches` and would share nothing with these four.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.checks.evaluation import CheckResult

if TYPE_CHECKING:
    from collections.abc import Iterable

    from practice.domain.checks.evaluation import CheckContext
    from practice.domain.ports import WorktreeStatus

__all__ = ["index_staged", "unmerged_paths_empty", "worktree_clean"]


def worktree_clean(context: CheckContext) -> CheckResult:
    """`worktree_clean {include_untracked?}` — nothing staged or half-finished.

    **Untracked files are ignored by default**, which is PLAN.md §6.5 and is worth
    restating because it looks like a leniency bug and is not: a scratch file
    someone created while poking around must not fail them, and poking around is
    the skill these exercises teach. An exercise that genuinely cares — one whose
    answer is "and clean up after yourself" — writes `{include_untracked: true}`.

    The two definitions live on `WorktreeStatus` rather than here, so the real
    adapter and the fake cannot drift apart about which one a check asked for.
    """
    strict = context.params.flag("include_untracked", default=False)
    status = context.query.status()
    clean = status.is_pristine if strict else status.is_clean
    return CheckResult(
        passed=clean,
        expected="a clean worktree"
        + (" with no untracked files" if strict else " (untracked files ignored)"),
        actual="clean" if clean else _describe_status(status, strict=strict),
    )


def index_staged(context: CheckContext) -> CheckResult:
    """`index_staged {paths}` — every named path has a change staged.

    Every one, not any: an author listing two paths means both, and "at least one of
    these is staged" is a claim nobody writes on purpose.

    A rename counts as its new path only. The old one no longer exists, so naming it
    would be asking about a file the solver correctly got rid of.
    """
    paths = context.params.paths("paths")
    staged = context.query.status().staged
    missing = [path for path in paths if path not in staged]
    return CheckResult(
        passed=not missing,
        expected=f"staged changes to {_join(paths)}",
        actual="all staged" if not missing else f"not staged: {_join(missing)}",
    )


def unmerged_paths_empty(context: CheckContext) -> CheckResult:
    """`unmerged_paths_empty` — no path is still mid-merge.

    Separate from `worktree_clean` even though a clean worktree implies it, because
    the two failures mean different things. "You have uncommitted changes" and "you
    are in the middle of a conflict" send a solver to different commands, and the
    second is the one where `git status` is about to be the most useful thing they
    read.
    """
    unmerged = context.query.status().unmerged
    return CheckResult(
        passed=not unmerged,
        expected="no unmerged paths",
        actual="none" if not unmerged else f"unmerged: {_join(sorted(unmerged))}",
    )


def _describe_status(status: WorktreeStatus, *, strict: bool) -> str:
    """What is dirty, by kind, so the report says what to do about it.

    "the worktree is not clean" is correct and useless. Naming the paths and which
    bucket each is in is the difference between a solver knowing to commit, to
    discard, or to finish a merge.
    """
    parts = []
    if status.staged:
        parts.append(f"staged: {_join(sorted(status.staged))}")
    if status.unstaged:
        parts.append(f"unstaged: {_join(sorted(status.unstaged))}")
    if status.unmerged:
        parts.append(f"unmerged: {_join(sorted(status.unmerged))}")
    if strict and status.untracked:
        parts.append(f"untracked: {_join(sorted(status.untracked))}")
    return "; ".join(parts)


def _join(paths: Iterable[str]) -> str:
    return ", ".join(paths)
