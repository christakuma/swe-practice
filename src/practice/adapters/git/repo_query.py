"""`RepoQuery` over a real repository, by running git and parsing what it says.

Satisfies `practice.domain.ports.RepoQuery` structurally, like every adapter
here (ADR 0002). Five decisions in it are worth more than the code.

**Machine-readable formats only.** `status --porcelain=v2`, `for-each-ref` with
an explicit `--format`, `log` with NUL-separated fields. Never the human output:
it is explicitly not a stable interface, it is localised, and it changes between
git versions. The NUL separators matter more than they look — a commit subject
may contain anything, tabs and pipes included, so any printable delimiter is a
delimiter a fixture author could accidentally use.

**Every lookup answers `None` rather than raising.** A missing ref is a clean
assertion failure, never an error (PLAN.md §6.5): half the point of these
exercises is that the repository may be in a state nobody anticipated, and a
traceback in the verdict panel teaches nothing. So a non-zero exit from git is
read as "no", not as a fault — which also means this class never needs to know
which of git's exit codes mean what.

**It caches for the length of one grading pass.** Six checks on one exercise ask
`status()` and `refs()` between them, and a `git` process on Windows is the
slowest thing in the system by an order of magnitude. The cache is per instance
and the instance is per grading pass, so there is no staleness window: nothing
runs a command between two assertions. An instance kept across a solver's
commands would be wrong, which is why the factory is a call and not a singleton.

**Commands go through `run_tool`, never `run`.** They are trusted argv the
grading engine built for itself, and no exercise allowlist could gate them — the
author never wrote `for-each-ref` down (§8.1). The flip side is the rule stated
on the port: nothing user-typed may be interpolated into one of these, and
nothing here takes a caller's string without passing it as its own argv element.

**`read_blob` is text-faithful, not byte-faithful.** The sandbox decodes process
output with `errors="replace"` and normalises CRLF, so a blob round-tripped
through it is the blob's *text*. That is exactly right for the assertions, which
are regular expressions, and it is a real limitation for a binary blob — stated
here rather than discovered. No exercise commits one: `.gitattributes` pins LF
for the file types fixtures write.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from practice.domain.errors import InvalidValueError
from practice.domain.ids import Sha
from practice.domain.ports import CommitInfo, ReflogEntry, WorktreeStatus

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from practice.domain.attempt import CommandResult
    from practice.domain.ports import Workspace

__all__ = ["GIT_TIMEOUT_SECONDS", "GitRepoQuery"]

#: Every interrogation gets the same budget. Generous for a three-commit
#: repository and short enough that a grading pass cannot hang a request: a
#: `git` call that takes this long has gone wrong in a way no retry fixes.
GIT_TIMEOUT_SECONDS: Final = 15.0

#: NUL, as it arrives in git's *output*. See the module docstring: a subject can
#: contain any printable character, so a printable delimiter is one a fixture
#: author can break by accident.
_SEP: Final = "\x00"

#: How to *ask* for that NUL. `%x00` is git's own hex escape and expands when
#: git writes the line. A real NUL here instead goes into the argv, and Windows
#: `CreateProcess` refuses an argument containing one outright -- found by
#: running it, as a `ValueError: embedded null character` raised from inside
#: `subprocess` before git was ever started.
_ASK_SEP: Final = "%x00"

#: `log --format` fields, in the order `CommitInfo` wants them.
_LOG_FORMAT: Final = f"%H{_ASK_SEP}%T{_ASK_SEP}%P{_ASK_SEP}%s"

#: `for-each-ref --format`, for `refs()`. A space, not a NUL: `for-each-ref` does
#: not take `log`'s `%xNN` escapes, and it does not need to -- a git ref name may
#: not contain a space, so one field cannot swallow the other.
_REF_FORMAT: Final = "%(objectname) %(refname)"

#: `reflog --format`, for `reflog()`. `%gs` is the message git shows after the
#: colon in `git reflog`'s own output — "commit: add parser", "reset: moving to
#: HEAD@{3}" — which is what a `reflog_contains` pattern is written against.
_REFLOG_FORMAT: Final = f"%H{_ASK_SEP}%gs"

#: How many fields `_LOG_FORMAT` produces. A line with fewer is a format change,
#: and skipping it beats half-building a `CommitInfo` out of the wrong columns.
_LOG_FIELDS: Final = 4

_REFLOG_FIELDS: Final = 2
_REF_FIELDS: Final = 2

#: `status --porcelain=v2` line kinds. `1` is an ordinary change, `2` a rename
#: or copy, `u` an unmerged path, `?` untracked. `#` is a header and ignored.
_UNMERGED: Final = "u"
_UNTRACKED: Final = "?"

#: In `1`/`2` lines the second field is a two-character XY code: X is the index
#: state, Y the worktree state, `.` meaning unchanged.
_UNCHANGED: Final = "."
_XY_LENGTH: Final = 2

#: Where the path sits in a porcelain-v2 change line, by line kind. A `1` line is
#: `1 XY sub mH mI mW hH hI path`; a `2` line inserts a rename score before the
#: path, so it is one field later and carries `path<tab>origPath`. Getting this
#: wrong is silent -- the path parses as `R100 renamed.py` and every assertion
#: about it fails for a reason that looks like the solver's fault.
_PATH_INDEX: Final = {"1": 8, "2": 9}

#: An unmerged line puts its path at index 10.
_UNMERGED_FIELDS: Final = 11


class GitRepoQuery:
    """Satisfies `practice.domain.ports.RepoQuery` over one workspace.

    One instance per grading pass. The caches below are the reason: they make the
    22 assertions cheap to run together without any of them having to know that
    another already asked the same question.
    """

    __slots__ = (
        "_blobs",
        "_logs",
        "_reflogs",
        "_refs",
        "_revs",
        "_status",
        "_trees",
        "_workspace",
        "_worktree_files",
    )

    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace
        self._revs: dict[str, Sha | None] = {}
        self._trees: dict[str, Sha | None] = {}
        self._refs: Mapping[str, Sha] | None = None
        self._status: WorktreeStatus | None = None
        self._logs: dict[str, tuple[CommitInfo, ...]] = {}
        self._reflogs: dict[str, tuple[ReflogEntry, ...]] = {}
        self._blobs: dict[tuple[str, str], bytes | None] = {}
        self._worktree_files: dict[str, str | None] = {}

    # --- revisions ----------------------------------------------------------

    def rev_parse(self, rev: str) -> Sha | None:
        """Resolve any revision git accepts, or `None` if it does not resolve.

        `--verify` and the `^{commit}` peel are both load-bearing. Without
        `--verify`, `git rev-parse nonsense` prints the string back and exits 0,
        so an unresolvable name would come back as a `Sha` construction failure
        rather than a clean miss. Without the peel, an annotated tag resolves to
        the *tag object*, and `ref_points_at {ref: refs/tags/v1, target: HEAD}`
        would fail on a correct answer — the two hashes genuinely differ.
        """
        if rev not in self._revs:
            self._revs[rev] = self._sha(
                ["rev-parse", "--verify", "-q", f"{rev}^{{commit}}"]
            )
        return self._revs[rev]

    def tree_sha(self, rev: str) -> Sha | None:
        """The hash of the tree a revision commits.

        What `tree_equals` compares, and the reason it can tell `revert` from
        `reset --hard` apart from everything else: two commits with different
        identities and the same content have the same tree hash.
        """
        if rev not in self._trees:
            self._trees[rev] = self._sha(
                ["rev-parse", "--verify", "-q", f"{rev}^{{tree}}"]
            )
        return self._trees[rev]

    def is_ancestor(self, ancestor: Sha, descendant: Sha) -> bool:
        """Whether `ancestor` is reachable from `descendant`.

        `merge-base --is-ancestor` rather than a walk of our own: it is git's own
        answer, it is correct about every shape of history including a repository
        with grafts, and the exit code *is* the result.
        """
        result = self._git(
            ["merge-base", "--is-ancestor", ancestor.value, descendant.value]
        )
        return result.succeeded

    def subject(self, rev: str) -> str | None:
        """The commit's first message line, for `commit_subject_matches`."""
        commits = self.log(rev)
        return commits[0].subject if commits else None

    # --- refs ---------------------------------------------------------------

    def refs(self) -> Mapping[str, Sha]:
        """Every ref, full name to hash: `refs/heads/main`, `refs/tags/v1`.

        Full names rather than short ones, because `branch_exists {name: main}`
        and `tag_exists {name: main}` have to be able to disagree — a repository
        may legally have both, and a short-name map could not tell them apart.
        """
        if self._refs is None:
            self._refs = self._parse_refs(
                self._git(["for-each-ref", f"--format={_REF_FORMAT}"]).stdout
            )
        return self._refs

    def head_ref(self) -> str | None:
        """The ref `HEAD` points at, or `None` when HEAD is detached.

        `symbolic-ref` is the only honest way to ask. Comparing `rev_parse(HEAD)`
        against the branch refs cannot work: a detached HEAD sitting on a branch
        tip is still detached, and that is precisely the state
        `naive-detached-checkout.cmds` ends in.
        """
        result = self._git(["symbolic-ref", "-q", "HEAD"])
        if not result.succeeded:
            return None
        name = result.stdout.strip()
        return name or None

    # --- the worktree and the index ----------------------------------------

    def status(self) -> WorktreeStatus:
        """Staged, unstaged, untracked and unmerged paths.

        `--porcelain=v2` rather than v1 because v1 overloads one two-character
        column for both the index and the worktree *and* for the unmerged states,
        so `DD`/`AU`/`UU` have to be special-cased by hand. v2 gives each line a
        kind in its first field, which is the distinction `index_staged` and
        `unmerged_paths_empty` need to be separate assertions at all.
        """
        if self._status is None:
            self._status = self._parse_status(
                self._git(["status", "--porcelain=v2", "--untracked-files=all"]).stdout
            )
        return self._status

    def worktree_file(self, path: str) -> str | None:
        """The working tree's copy of `path`, or `None` if it is not readable.

        Through the workspace rather than through git, because the question is
        about a file on disk and not about anything git tracks — an untracked
        file a solver wrote is exactly the case `file_exists` is for.
        """
        if path not in self._worktree_files:
            self._worktree_files[path] = self._read_worktree_file(path)
        return self._worktree_files[path]

    def _read_worktree_file(self, path: str) -> str | None:
        """`None` for every way a read can fail, including a path escape.

        Three ways, and the third is the interesting one. `OSError` is the file not
        being there; `UnicodeDecodeError` is it not being text; `ValueError` is a
        `path:` that escapes the repository, which `SubprocessWorkspace` refuses
        with a `WorkspacePathError`. That is an authoring mistake, and its useful
        report is `<no such file>` in the verdict rather than a traceback.
        """
        try:
            return self._workspace.read_file(path)
        except (OSError, UnicodeDecodeError, ValueError):
            return None

    # --- history -------------------------------------------------------------

    def log(self, rev: str) -> Sequence[CommitInfo]:
        """First-parent-inclusive history of `rev`, newest first.

        Not `--first-parent`: `commit_count` and `linear_history` both have to
        see a merge's second parent — the first to count what is reachable, the
        second to notice the merge at all.
        """
        if rev not in self._logs:
            result = self._git(["log", f"--format={_LOG_FORMAT}", rev])
            self._logs[rev] = self._parse_log(result.stdout) if result.succeeded else ()
        return self._logs[rev]

    def reflog(self, ref: str) -> Sequence[ReflogEntry]:
        """Every position `ref` has held, newest first and index 0 first.

        The index is the position in this list rather than anything git prints,
        which is what makes it the `n` in `HEAD@{n}` — git's own `%gd` renders
        the whole selector and would have to be parsed back out.
        """
        if ref not in self._reflogs:
            result = self._git(["reflog", "show", f"--format={_REFLOG_FORMAT}", ref])
            self._reflogs[ref] = (
                self._parse_reflog(result.stdout) if result.succeeded else ()
            )
        return self._reflogs[ref]

    def stash_list(self) -> Sequence[str]:
        """One line per stash entry, newest first. Empty when there are none.

        `git stash list` exits 0 on a repository with no stash and prints
        nothing, so there is no missing-ref case to handle here.
        """
        result = self._git(["stash", "list", "--format=%gs"])
        if not result.succeeded:
            return ()
        return tuple(line for line in result.stdout.splitlines() if line)

    # --- content -------------------------------------------------------------

    def read_blob(self, rev: str, path: str) -> bytes | None:
        """A committed file's content at a revision, or `None` if it is not there.

        Text-faithful rather than byte-faithful — see the module docstring.
        """
        key = (rev, path)
        if key not in self._blobs:
            result = self._git(["show", f"{rev}:{path}"])
            self._blobs[key] = (
                result.stdout.encode("utf-8") if result.succeeded else None
            )
        return self._blobs[key]

    # --- what the fixture left behind ---------------------------------------

    def aliases(self) -> Mapping[str, Sha]:
        """The fixture's `@c1` names. Read from the workspace, not from git."""
        return self._workspace.aliases()

    def snapshot(self) -> Mapping[str, Sha]:
        """Every ref as the fixture left it, for `ref_unchanged`."""
        return self._workspace.snapshot()

    # --- the one place a process is started ---------------------------------

    def _git(self, arguments: Sequence[str]) -> CommandResult:
        """Run one git command through the workspace's trusted channel."""
        return self._workspace.run_tool(
            ["git", *arguments], timeout=GIT_TIMEOUT_SECONDS
        )

    def _sha(self, arguments: Sequence[str]) -> Sha | None:
        """Run a command expected to print one hash, tolerating every failure.

        A non-zero exit means the revision does not resolve. Output that is not a
        hash means git printed something this code did not expect, which is the
        same answer from an assertion's point of view and a much better one than
        a `ValueError` surfacing from inside a verdict.
        """
        result = self._git(arguments)
        if not result.succeeded:
            return None
        return _as_sha(result.stdout.strip())

    # --- parsing -------------------------------------------------------------

    @staticmethod
    def _parse_refs(text: str) -> Mapping[str, Sha]:
        found: dict[str, Sha] = {}
        for line in text.splitlines():
            fields = line.split(" ")
            if len(fields) != _REF_FIELDS:
                continue
            sha = _as_sha(fields[0].strip())
            name = fields[1].strip()
            if sha is not None and name:
                found[name] = sha
        return found

    @staticmethod
    def _parse_log(text: str) -> tuple[CommitInfo, ...]:
        commits: list[CommitInfo] = []
        for line in text.splitlines():
            fields = line.split(_SEP)
            if len(fields) != _LOG_FIELDS:
                continue
            sha = _as_sha(fields[0])
            tree = _as_sha(fields[1])
            if sha is None or tree is None:
                continue
            parents = tuple(
                parent
                for parent in (_as_sha(raw) for raw in fields[2].split())
                if parent is not None
            )
            commits.append(
                CommitInfo(sha=sha, tree=tree, subject=fields[3], parents=parents)
            )
        return tuple(commits)

    @staticmethod
    def _parse_reflog(text: str) -> tuple[ReflogEntry, ...]:
        entries: list[ReflogEntry] = []
        for index, line in enumerate(text.splitlines()):
            fields = line.split(_SEP)
            if len(fields) != _REFLOG_FIELDS:
                continue
            sha = _as_sha(fields[0])
            if sha is None:
                continue
            entries.append(ReflogEntry(index=index, sha=sha, message=fields[1]))
        return tuple(entries)

    @staticmethod
    def _parse_status(text: str) -> WorktreeStatus:
        """Split porcelain v2 into the four sets an assertion asks about.

        A rename contributes only its *new* path. The old one no longer exists,
        so `index_staged {paths: [...]}` naming it would be asking about a file
        the solver correctly got rid of.
        """
        staged: set[str] = set()
        unstaged: set[str] = set()
        untracked: set[str] = set()
        unmerged: set[str] = set()

        for line in text.splitlines():
            fields = line.split(" ")
            kind = fields[0]
            if kind == _UNTRACKED and len(fields) > 1:
                untracked.add(_porcelain_path(" ".join(fields[1:])))
            elif kind == _UNMERGED and len(fields) >= _UNMERGED_FIELDS:
                unmerged.add(_porcelain_path(" ".join(fields[10:])))
            elif kind in _PATH_INDEX and len(fields) > _PATH_INDEX[kind]:
                xy = fields[1]
                path = _porcelain_path(" ".join(fields[_PATH_INDEX[kind] :]))
                if len(xy) != _XY_LENGTH:
                    continue
                if xy[0] != _UNCHANGED:
                    staged.add(path)
                if xy[1] != _UNCHANGED:
                    unstaged.add(path)

        return WorktreeStatus(
            staged=frozenset(staged),
            unstaged=frozenset(unstaged),
            untracked=frozenset(untracked),
            unmerged=frozenset(unmerged),
        )


def _porcelain_path(raw: str) -> str:
    """The path from a porcelain-v2 line, forward-slashed and rename-aware.

    A `2` line is `<path>\\t<original path>`; only the new path is wanted. Paths
    are already forward-slashed by git on every platform, but `WorktreeStatus`
    promises it, and promising it in one place beats asserting it in four.
    """
    return raw.split("\t", 1)[0].strip().replace("\\", "/")


def _as_sha(raw: str) -> Sha | None:
    """A `Sha`, or `None` for anything that is not one.

    Git is not supposed to print a non-hash where a hash was asked for, so this
    is not defensive about git being wrong — it is defensive about *us* having
    asked the wrong question, which a future `--format` edit makes easy. The
    failure mode it removes is an `InvalidValueError` escaping a grading pass.
    """
    value = raw.strip()
    try:
        return Sha(value)
    except InvalidValueError:
        return None
