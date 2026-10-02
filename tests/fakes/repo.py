"""A repository in memory, so 22 assertions can be tested without git.

The fake that pays for the `RepoQuery` port. Every check function is a pure
function over this protocol, so the whole assertion vocabulary gets full unit
coverage in milliseconds, with no subprocess, no temp directory and no git
installed (PLAN.md §6.2). That is the difference between a check engine you can
refactor and one you are afraid of.

**It computes rather than stores.** `is_ancestor` walks the parent links,
`rev_parse("HEAD~2")` counts back through them, `log` collects what is reachable.
A fake that stored the answers would agree with whatever the test asserted and
prove nothing; this one can be *wrong*, which is what makes the conformance suite
in `tests/integration/git/` meaningful.

**Hashes are invented, not computed.** A fake that produced git's real SHAs would
have to be git. So `commit()` assigns a hash from a counter, and no test compares
a fake hash to a real one — the conformance suite builds the fake *from* a real
repository's data and then compares the *derived* answers, which is the part both
implementations work out for themselves.

The revision grammar is a documented subset: `HEAD`, a full or short ref name, a
full or abbreviated hash, `~n`, `^`, `^n`, and `<ref>@{n}`. Anything else resolves
to `None`. That is everything the content library uses and everything the
assertions accept; the conformance suite is what proves the subset agrees with
git rather than merely existing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final

from practice.domain.ids import Sha
from practice.domain.ports import CommitInfo, ReflogEntry, WorktreeStatus

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

__all__ = ["Commit", "FakeRepoQuery", "RepoBuilder", "RepoState", "a_repo"]

#: `<rev>~<n>` and `<rev>^<n>`, with the count optional.
_ANCESTOR_STEP: Final = re.compile(r"^(?P<base>.+?)(?P<operator>[~^])(?P<count>\d*)$")

#: `<ref>@{<n>}` — a reflog position.
_REFLOG_SELECTOR: Final = re.compile(r"^(?P<ref>.+)@\{(?P<index>\d+)\}$")

_HEX: Final = re.compile(r"^[0-9a-f]+$")

#: The shortest prefix a test may abbreviate a hash to, matching git's own floor.
_MIN_ABBREV: Final = 4

#: Where a short name may live, in the order git itself searches.
_REF_PREFIXES: Final = ("refs/heads/", "refs/tags/", "refs/remotes/")


#: Leading nibble per object kind, so a commit and its tree cannot collide —
#: `tree_equals` compares trees, and a test that accidentally compared a commit
#: to itself would pass for the wrong reason. Both are hex, because `Sha`
#: rightly refuses anything that is not.
_COMMIT_NIBBLE: Final = "c"
_TREE_NIBBLE: Final = "a"


def _invent_sha(seed: int, *, kind: str) -> Sha:
    """A distinct, valid 40-hex hash per object, derived from a counter.

    **Unique within one builder, not across the process.** Two `a_repo()` calls
    hand out the same hashes, which is the right trade — a hash that depended on
    test execution order would make a failure message unreproducible — but it
    means a test wanting a hash the repository has never heard of should write a
    literal rather than borrow one from a second builder.
    """
    return Sha(f"{kind}{seed:0>39x}"[:40])


@dataclass(frozen=True, slots=True)
class Commit:
    """One node of the fake's DAG.

    Public rather than private because the conformance suite builds these out of a
    real repository's log, which is the only way a fake can be compared to git at
    all (see `tests/integration/git/test_conformance.py`).
    """

    sha: Sha
    tree: Sha
    subject: str
    parents: tuple[Sha, ...]

    def info(self) -> CommitInfo:
        return CommitInfo(
            sha=self.sha, tree=self.tree, subject=self.subject, parents=self.parents
        )


@dataclass(frozen=True, slots=True)
class RepoState:
    """Everything the fake answers from, in one value.

    A single argument rather than eleven keyword parameters, which is the shape
    that keeps `FakeRepoQuery.__init__` a constructor instead of a form. It is
    also the thing the conformance suite builds out of a *real* repository, so
    naming it is what makes that suite expressible.
    """

    commits: Mapping[Sha, Commit] = field(default_factory=dict)
    refs: Mapping[str, Sha] = field(default_factory=dict)
    aliases: Mapping[str, Sha] = field(default_factory=dict)
    snapshot: Mapping[str, Sha] = field(default_factory=dict)
    reflogs: Mapping[str, tuple[ReflogEntry, ...]] = field(default_factory=dict)
    stashes: tuple[str, ...] = ()
    blobs: Mapping[tuple[Sha, str], bytes] = field(default_factory=dict)
    worktree: Mapping[str, str] = field(default_factory=dict)
    worktree_status: WorktreeStatus = field(default_factory=WorktreeStatus)
    head: str | None = "refs/heads/main"
    detached_at: Sha | None = None


@dataclass(slots=True)
class RepoBuilder:
    """Builds a `FakeRepoQuery` out of a few readable lines.

    The point of the builder is that a test about one assertion reads as a
    sentence about repository shape rather than as a wall of hashes:

        repo = a_repo()
        c1 = repo.commit("add build script", alias="c1")
        c2 = repo.commit("add parser", alias="c2")
        repo.branch("main", c2)
        query = repo.build()
    """

    _commits: dict[Sha, Commit] = field(default_factory=dict)
    _order: list[Sha] = field(default_factory=list)
    _refs: dict[str, Sha] = field(default_factory=dict)
    _aliases: dict[str, Sha] = field(default_factory=dict)
    _snapshot: dict[str, Sha] = field(default_factory=dict)
    _reflogs: dict[str, list[ReflogEntry]] = field(default_factory=dict)
    _stashes: list[str] = field(default_factory=list)
    _blobs: dict[tuple[Sha, str], bytes] = field(default_factory=dict)
    _worktree: dict[str, str] = field(default_factory=dict)
    _status: WorktreeStatus = field(default_factory=WorktreeStatus)
    _head: str | None = "refs/heads/main"
    _detached_at: Sha | None = None
    _counter: int = 0

    # --- building ------------------------------------------------------------

    def commit(
        self,
        subject: str,
        *,
        parents: Sequence[Sha] = (),
        alias: str | None = None,
        tree: Sha | None = None,
        files: Mapping[str, str] | None = None,
    ) -> Sha:
        """Add a commit and return its hash.

        `tree` is explicit so a test can give two commits the *same* tree, which
        is the entire subject of `tree_equals` and the reason `revert` and
        `reset --hard` are distinguishable at all.
        """
        self._counter += 1
        sha = _invent_sha(self._counter, kind=_COMMIT_NIBBLE)
        self._commits[sha] = Commit(
            sha=sha,
            tree=(
                tree
                if tree is not None
                else _invent_sha(self._counter, kind=_TREE_NIBBLE)
            ),
            subject=subject,
            parents=tuple(parents),
        )
        self._order.append(sha)
        if alias is not None:
            self._aliases[alias] = sha
        for path, content in (files or {}).items():
            self._blobs[(sha, path)] = content.encode("utf-8")
        return sha

    def chain(self, *subjects: str, alias_prefix: str = "c") -> tuple[Sha, ...]:
        """A linear run of commits, aliased `c1`, `c2`, … like a real fixture."""
        shas: list[Sha] = []
        for index, subject in enumerate(subjects, start=1):
            parents = (shas[-1],) if shas else ()
            shas.append(
                self.commit(subject, parents=parents, alias=f"{alias_prefix}{index}")
            )
        return tuple(shas)

    def branch(self, name: str, sha: Sha, *, snapshot: bool = True) -> RepoBuilder:
        return self.ref(f"refs/heads/{name}", sha, snapshot=snapshot)

    def tag(self, name: str, sha: Sha, *, snapshot: bool = True) -> RepoBuilder:
        return self.ref(f"refs/tags/{name}", sha, snapshot=snapshot)

    def remote(
        self, name: str, sha: Sha, *, remote: str = "origin", snapshot: bool = True
    ) -> RepoBuilder:
        return self.ref(f"refs/remotes/{remote}/{name}", sha, snapshot=snapshot)

    def ref(self, name: str, sha: Sha, *, snapshot: bool = True) -> RepoBuilder:
        """Point a full ref name at a commit.

        `snapshot` defaults to true because a fixture's refs are what the snapshot
        holds; a test about `ref_unchanged` sets it false on the ref it means to
        have moved, which is the only way to express "this ref moved during the
        attempt".
        """
        self._refs[name] = sha
        if snapshot:
            self._snapshot[name] = sha
        return self

    def moved(self, name: str, sha: Sha) -> RepoBuilder:
        """Point a ref somewhere new without touching the fixture snapshot."""
        self._refs[name] = sha
        return self

    def head(self, ref: str) -> RepoBuilder:
        """Attach HEAD to a full ref name."""
        self._head = ref
        self._detached_at = None
        return self

    def detach(self, sha: Sha) -> RepoBuilder:
        """Leave HEAD detached at a commit — the `head_detached` case."""
        self._head = None
        self._detached_at = sha
        return self

    def reflog(self, ref: str, entries: Iterable[tuple[Sha, str]]) -> RepoBuilder:
        """Positions newest first; the index is the `n` in `<ref>@{n}`."""
        self._reflogs[ref] = [
            ReflogEntry(index=index, sha=sha, message=message)
            for index, (sha, message) in enumerate(entries)
        ]
        return self

    def stash(self, *messages: str) -> RepoBuilder:
        self._stashes.extend(messages)
        return self

    def status(
        self,
        *,
        staged: Iterable[str] = (),
        unstaged: Iterable[str] = (),
        untracked: Iterable[str] = (),
        unmerged: Iterable[str] = (),
    ) -> RepoBuilder:
        """The four sets `WorktreeStatus` holds. Named rather than `**kwargs`, so
        a typo is a type error instead of a silently empty set.
        """
        self._status = WorktreeStatus(
            staged=frozenset(staged),
            unstaged=frozenset(unstaged),
            untracked=frozenset(untracked),
            unmerged=frozenset(unmerged),
        )
        return self

    def working_file(self, path: str, content: str) -> RepoBuilder:
        """A file in the working tree, which is not the same as a committed blob —
        the distinction `file_matches` and `file_at_ref_matches` exist to make.
        """
        self._worktree[path] = content
        return self

    def build(self) -> FakeRepoQuery:
        return FakeRepoQuery(
            RepoState(
                commits=dict(self._commits),
                refs=dict(self._refs),
                aliases=dict(self._aliases),
                snapshot=dict(self._snapshot),
                reflogs={ref: tuple(entries) for ref, entries in self._reflogs.items()},
                stashes=tuple(self._stashes),
                blobs=dict(self._blobs),
                worktree=dict(self._worktree),
                worktree_status=self._status,
                head=self._head,
                detached_at=self._detached_at,
            )
        )


def a_repo() -> RepoBuilder:
    """A fresh builder. Named as a sentence, like the other fake builders."""
    return RepoBuilder()


class FakeRepoQuery:
    """Satisfies `practice.domain.ports.RepoQuery` with no filesystem at all."""

    __slots__ = ("_state",)

    def __init__(self, state: RepoState) -> None:
        self._state = state

    # --- revisions ----------------------------------------------------------

    def rev_parse(self, rev: str) -> Sha | None:
        """Resolve the documented subset of git's revision grammar.

        Order matters and mirrors git's: the reflog selector and the ancestry
        operators are suffixes, so they are peeled before a name lookup, or
        `HEAD~1` would be looked up as a ref called `HEAD~1` and miss.
        """
        rev = rev.strip()
        if not rev:
            return None

        selector = _REFLOG_SELECTOR.match(rev)
        if selector is not None:
            entries = self._state.reflogs.get(selector["ref"], ())
            index = int(selector["index"])
            return entries[index].sha if index < len(entries) else None

        step = _ANCESTOR_STEP.match(rev)
        if step is not None:
            return self._walk(step["base"], step["operator"], step["count"])

        return self._name(rev)

    def _walk(self, base: str, operator: str, count: str) -> Sha | None:
        """`~n` walks n generations of first parents; `^n` takes the nth parent.

        `^` with no number means `^1`, and `~` with no number means `~1`, which is
        what git does. `~0` and `^0` both mean the commit itself.
        """
        start = self.rev_parse(base)
        if start is None:
            return None
        number = int(count) if count else 1

        if operator == "^":
            if number == 0:
                return start
            commit = self._state.commits.get(start)
            if commit is None or number > len(commit.parents):
                return None
            return commit.parents[number - 1]

        current = start
        for _ in range(number):
            commit = self._state.commits.get(current)
            if commit is None or not commit.parents:
                return None
            current = commit.parents[0]
        return current

    def _name(self, rev: str) -> Sha | None:
        """A ref name, HEAD, or a full or abbreviated hash."""
        if rev == "HEAD":
            return self._head_sha()
        if rev in self._state.refs:
            return self._state.refs[rev]
        for prefix in _REF_PREFIXES:
            if f"{prefix}{rev}" in self._state.refs:
                return self._state.refs[f"{prefix}{rev}"]
        return self._by_hash(rev)

    def _by_hash(self, rev: str) -> Sha | None:
        """An exact or abbreviated hash, refusing an ambiguous abbreviation.

        Ambiguity resolves to `None` rather than to an arbitrary match, because
        git itself refuses it — and an assertion that silently picked one of two
        candidates would be unreproducible in exactly the way §6.1 is about.
        """
        candidate = rev.lower()
        if not _HEX.match(candidate) or len(candidate) < _MIN_ABBREV:
            return None
        matches = [
            sha for sha in self._state.commits if sha.value.startswith(candidate)
        ]
        return matches[0] if len(matches) == 1 else None

    def _head_sha(self) -> Sha | None:
        if self._state.head is not None:
            return self._state.refs.get(self._state.head)
        return self._state.detached_at

    def tree_sha(self, rev: str) -> Sha | None:
        sha = self.rev_parse(rev)
        commit = self._state.commits.get(sha) if sha is not None else None
        return commit.tree if commit is not None else None

    def is_ancestor(self, ancestor: Sha, descendant: Sha) -> bool:
        """Reachability, by walking parents. Reflexive, like git's own answer.

        `git merge-base --is-ancestor X X` exits 0, so this returns `True` for a
        commit and itself. Worth matching rather than arguing with: the revert
        scenario's `history-preserved` check compares `@c3` against `HEAD`, and on
        a solution that reverted and pushed nothing, those are the same commit.
        """
        if ancestor == descendant:
            return ancestor in self._state.commits
        seen: set[Sha] = set()
        frontier = [descendant]
        while frontier:
            current = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            if current == ancestor:
                return True
            commit = self._state.commits.get(current)
            if commit is not None:
                frontier.extend(commit.parents)
        return False

    def subject(self, rev: str) -> str | None:
        sha = self.rev_parse(rev)
        commit = self._state.commits.get(sha) if sha is not None else None
        return commit.subject if commit is not None else None

    # --- refs ---------------------------------------------------------------

    def refs(self) -> Mapping[str, Sha]:
        return dict(self._state.refs)

    def head_ref(self) -> str | None:
        return self._state.head

    # --- the worktree and the index ----------------------------------------

    def status(self) -> WorktreeStatus:
        return self._state.worktree_status

    def worktree_file(self, path: str) -> str | None:
        return self._state.worktree.get(path)

    # --- history ------------------------------------------------------------

    def log(self, rev: str) -> Sequence[CommitInfo]:
        """Everything reachable from `rev`, newest first.

        Ordered by a breadth-first walk that emits a commit only once every path
        to it has been seen, so a merge's two sides do not interleave
        arbitrarily. Exact ordering between independent branches is *not*
        guaranteed to match git's date-based order — no assertion depends on it,
        and the conformance suite compares the reachable *set* rather than the
        sequence for that reason.
        """
        start = self.rev_parse(rev)
        if start is None or start not in self._state.commits:
            return ()

        ordered: list[CommitInfo] = []
        seen: set[Sha] = set()
        frontier = [start]
        while frontier:
            current = frontier.pop(0)
            if current in seen:
                continue
            commit = self._state.commits.get(current)
            if commit is None:
                continue
            seen.add(current)
            ordered.append(commit.info())
            frontier.extend(commit.parents)
        return tuple(ordered)

    def reflog(self, ref: str) -> Sequence[ReflogEntry]:
        return self._state.reflogs.get(ref, ())

    def stash_list(self) -> Sequence[str]:
        return self._state.stashes

    # --- content ------------------------------------------------------------

    def read_blob(self, rev: str, path: str) -> bytes | None:
        sha = self.rev_parse(rev)
        if sha is None:
            return None
        return self._state.blobs.get((sha, path))

    # --- what the fixture left behind ---------------------------------------

    def aliases(self) -> Mapping[str, Sha]:
        return dict(self._state.aliases)

    def snapshot(self) -> Mapping[str, Sha]:
        return dict(self._state.snapshot)
