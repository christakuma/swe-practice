"""Proof that the two `RepoQuery` implementations answer the same questions.

The whole case for the port rests on this file. Twenty-two assertions are
unit-tested against `FakeRepoQuery` in milliseconds, and that is only evidence
about the real thing if the fake agrees with real git — otherwise the unit suite
is 20 tests agreeing with each other and with nothing else.

**How a fake can be compared to git at all.** It cannot produce git's hashes
without being git, so the comparison cannot start from a shared literal. Instead
the fake is *loaded* from a real repository's raw data — its refs, its full commit
list, its status — and then both implementations are asked the questions neither
was given the answer to:

*Loaded, so agreement is trivial:* `refs`, `status`, `stash_list`, `aliases`,
`snapshot`, `head_ref`, and the reflog positions behind `<ref>@{n}`.

*Derived, so agreement is the test:* `rev_parse` over eleven spellings,
`tree_sha`, `subject`, `is_ancestor` over every ordered pair of commits, `log`
reachability, which commits are merges.

**The reflog spellings moved from the second list to the first in Phase 11**, and
it is a real if small loss worth recording. `RepoQuery.reflog` was deleted with
`reflog_contains`, and it had been the channel this suite loaded reflog positions
through — so the fake is now seeded by asking the real adapter to resolve each
`<ref>@{n}` in turn, which makes comparing those three spellings circular. They
are therefore no longer compared here. The real adapter's own resolution of
`HEAD@{3}` is still covered directly by `test_repo_query.py`, and the fake's by
`tests/unit/fakes/test_repo.py`; what is gone is the cross-check between them.

Only the right-hand column proves anything, and it is the column every assertion
in `domain/checks/` actually reads. The loaded fields are compared anyway, cheaply,
because a loader that dropped a ref would silently weaken everything below it.

**Run against both real scenarios, in several states.** A conformance suite over a
pristine fixture would miss every interesting case: the states that matter are the
ones a solver reaches — a revert, a `reset --hard`, a detached HEAD, a merge, a
dirty worktree. Each is reached by replaying commands through the real policy,
which is also the only path a solver has.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.sandbox import SubprocessSandboxProvisioner
from practice.config import content_root
from practice.domain.ids import AttemptId, ExerciseId
from practice.domain.ports import WorktreeStatus
from tests.fakes import Commit, FakeRepoQuery, RepoState
from tests.integration.git.conftest import (
    FLAGSHIP,
    RECOVERY,
    Provision,
    exercise,
    query,
    replay,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
    from pathlib import Path

    from practice.adapters.content import FilesystemContentRepository
    from practice.adapters.git import GitRepoQuery
    from practice.adapters.sandbox import SubprocessWorkspace
    from practice.domain.ids import Sha
    from practice.domain.ports import CommitInfo

#: Working-tree paths both implementations are asked about. Two that the fixtures
#: create, one a solver might, and one that is never there.
PATHS = ("build.sh", "parser.py", "notes.md", "no-such-file.txt")

#: Revision spellings to compare. Every one of them appears in a shipped `with:`
#: mapping, in a `.cmds` file, or in the fake's documented grammar — so this list
#: is the resolution surface the check engine leans on rather than a wishlist.
SPELLINGS = (
    "HEAD",
    "HEAD~1",
    "HEAD~2",
    "HEAD^",
    "main",
    "refs/heads/main",
    "refs/remotes/origin/main",
    "refs/heads/feature/csv-export",
    "refs/heads/does-not-exist",
    "nonsense",
    "",
)


def load(real: GitRepoQuery) -> FakeRepoQuery:
    """Build a fake from a real repository's raw data.

    Everything here is a direct read. Nothing is computed, which is the point: the
    questions the comparison then asks are ones the fake has to work out for
    itself from the commit graph it was handed.

    `_every_commit` is how the whole graph is collected rather than one branch's:
    a commit no ref points at is the entire premise of `recover-a-lost-commit`,
    and a fake loaded only from reachable history could not represent it.
    """
    commits = {
        commit.sha: Commit(
            sha=commit.sha,
            tree=commit.tree,
            subject=commit.subject,
            parents=commit.parents,
        )
        for commit in _every_commit(real)
    }
    blobs = {
        (sha, path): blob
        for sha in commits
        for path in PATHS
        if (blob := real.read_blob(sha.value, path)) is not None
    }
    worktree = {
        path: content
        for path in PATHS
        if (content := real.worktree_file(path)) is not None
    }
    return FakeRepoQuery(
        RepoState(
            commits=commits,
            refs=dict(real.refs()),
            aliases=dict(real.aliases()),
            snapshot=dict(real.snapshot()),
            reflogs={ref: _reflog_positions(real, ref) for ref in _REFLOGGED},
            stashes=tuple(real.stash_list()),
            blobs=blobs,
            worktree=worktree,
            worktree_status=real.status(),
            head=real.head_ref(),
            detached_at=real.rev_parse("HEAD") if real.head_ref() is None else None,
        )
    )


#: Refs whose reflog positions are loaded, so that the fake can resolve
#: `<ref>@{n}` at all. `HEAD`'s is the one a `.cmds` file ever names; the branch
#: reflogs are loaded because real git has them and a fake that did not would
#: differ from it in a way nothing here would notice.
_REFLOGGED = ("HEAD", "refs/heads/main", "refs/heads/feature/csv-export")

#: How far to probe a ref's reflog. Deeper than any fixture reaches, so the
#: positions are loaded in full rather than truncated at a length that happens
#: to be enough today.
_REFLOG_DEPTH = 32


def _reflog_positions(real: GitRepoQuery, ref: str) -> tuple[Sha, ...]:
    """Every position `ref` has held, newest first, read through `rev_parse`.

    The replacement for the deleted `RepoQuery.reflog`. It stops at the first
    index that does not resolve, which is what git does too — `HEAD@{99}` on a
    short reflog is an error, not an empty answer.
    """
    positions: list[Sha] = []
    for index in range(_REFLOG_DEPTH):
        found = real.rev_parse(f"{ref}@{{{index}}}")
        if found is None:
            break
        positions.append(found)
    return tuple(positions)


def _every_commit(real: GitRepoQuery) -> Sequence[CommitInfo]:
    """Every commit in the repository, reachable or not.

    `--all` and `--reflog` passed where `log` documents a revision. A mild abuse,
    and the right one here, because **`--all` alone is not enough and this suite is
    what proved it.** `--all` walks refs, and the whole premise of
    `recover-a-lost-commit` is two commits no ref points at any more: the fake
    resolved `HEAD@{3}` correctly, because a reflog entry carries its own hash, and
    then had no commit object to answer `tree_sha` or `subject` from. Eight failures
    in one state of one scenario, which is exactly the class of gap a fake quietly
    carries when nothing compares it to the real thing.
    """
    found = {commit.sha: commit for commit in real.log("--all")}
    found.update({commit.sha: commit for commit in real.log("--reflog")})
    return tuple(found.values())


# --- the states to compare in ----------------------------------------------


def _pristine(workspace: SubprocessWorkspace) -> None:
    """Straight out of the fixture. The baseline every other state diverges from."""
    del workspace


def _reverted(workspace: SubprocessWorkspace) -> None:
    replay(workspace, "git revert --no-edit HEAD\n")


def _reset_hard(workspace: SubprocessWorkspace) -> None:
    replay(workspace, "git reset --hard HEAD~1\n")


def _detached(workspace: SubprocessWorkspace) -> None:
    """A detached HEAD, which is the state `head_ref` exists for."""
    replay(workspace, "git checkout HEAD~1\n")


def _dirty(workspace: SubprocessWorkspace) -> None:
    """One path in each of the three ordinary status buckets, plus a stash."""
    replay(
        workspace,
        'write staged.txt "indexed"\n'
        "git add staged.txt\n"
        'write parser.py "modified but not staged"\n'
        'write notes.md "a scratch file"\n',
    )


def _merged(workspace: SubprocessWorkspace) -> None:
    """A real merge commit, so `log` has a node with two parents in it."""
    replay(
        workspace,
        "git checkout -b side HEAD~2\n"
        'write side.txt "from the side branch"\n'
        "git add side.txt\n"
        "git commit -m side-work\n"
        "git checkout main\n"
        "git merge --no-ff --no-edit side\n",
    )


STATES: Mapping[str, Callable[[SubprocessWorkspace], None]] = {
    "pristine": _pristine,
    "reverted": _reverted,
    "reset-hard": _reset_hard,
    "detached": _detached,
    "dirty": _dirty,
    "merged": _merged,
}

#: Every (scenario, state) combination, each provisioned **once per module**.
#:
#: Function scope is the default and was the first draft, and it does not finish:
#: forty-odd comparisons times twelve repositories is five hundred fixture runs,
#: which is a suite nobody waits for and therefore a suite nobody runs. Module
#: scope is honest here rather than merely fast -- the state is reached before
#: either implementation is built, and nothing below mutates the repository, so
#: sharing one cannot make a later test depend on an earlier one.
COMBINATIONS = [
    (exercise_id, state)
    for exercise_id in (FLAGSHIP, RECOVERY)
    for state in sorted(STATES)
]


def _combination_id(combination: tuple[ExerciseId, str]) -> str:
    exercise_id, state = combination
    return f"{exercise_id.slug}:{state}"


@pytest.fixture(scope="module", params=COMBINATIONS, ids=_combination_id)
def pair(
    request: pytest.FixtureRequest,
    tmp_path_factory: pytest.TempPathFactory,
    tools: tuple[Path, Path],
    content: FilesystemContentRepository,
) -> Iterator[tuple[GitRepoQuery, FakeRepoQuery]]:
    """One real repository in one state, and a fake loaded from it.

    The state is reached before either implementation is built, so both see the
    same repository -- a fake loaded first and compared after would be comparing
    two moments as well as two implementations.
    """
    del tools  # requested so a missing tool fails here, not mid-fixture
    exercise_id, state = request.param
    index = COMBINATIONS.index((exercise_id, state))
    provisioner = SubprocessSandboxProvisioner(
        content_root=content_root(),
        workspace_root=tmp_path_factory.mktemp("conformance"),
    )
    workspace = provisioner.provision(
        exercise(content, exercise_id),
        AttemptId.parse(f"{index:08x}-0000-4000-8000-000000000000"),
    )
    try:
        STATES[state](workspace)
        real = query(workspace)
        yield real, load(real)
    finally:
        workspace.dispose()


# --- the loaded fields, compared cheaply ------------------------------------


def test_they_hold_the_same_refs_aliases_and_snapshot(
    pair: tuple[GitRepoQuery, FakeRepoQuery],
) -> None:
    """Trivially true by construction, and worth asserting anyway: a loader that
    dropped a ref would silently weaken every derived comparison below.
    """
    real, fake = pair

    assert dict(fake.refs()) == dict(real.refs())
    assert dict(fake.aliases()) == dict(real.aliases())
    assert dict(fake.snapshot()) == dict(real.snapshot())
    assert fake.head_ref() == real.head_ref()
    assert tuple(fake.stash_list()) == tuple(real.stash_list())


def test_they_report_the_same_worktree_status(
    pair: tuple[GitRepoQuery, FakeRepoQuery],
) -> None:
    """And agree on the two derived properties, which is the part that is not
    trivial: `worktree_clean`'s default lives on `WorktreeStatus` precisely so
    both implementations cannot disagree about what clean means.
    """
    real, fake = pair

    assert fake.status() == real.status()
    assert fake.status().is_clean == real.status().is_clean
    assert fake.status().is_pristine == real.status().is_pristine


# --- the derived answers, which is the actual test -------------------------


@pytest.mark.parametrize("spelling", SPELLINGS)
def test_they_resolve_a_revision_to_the_same_commit(
    pair: tuple[GitRepoQuery, FakeRepoQuery], spelling: str
) -> None:
    """Including the misses. A spelling that resolves in one and not the other is
    the worst available outcome: the assertion silently grades a different commit.
    """
    real, fake = pair

    assert fake.rev_parse(spelling) == real.rev_parse(spelling), spelling


@pytest.mark.parametrize("spelling", SPELLINGS)
def test_they_resolve_a_revision_to_the_same_tree(
    pair: tuple[GitRepoQuery, FakeRepoQuery], spelling: str
) -> None:
    """What `tree_equals` compares, and the only thing that can tell a revert from
    a reset: the trees are identical and the commits are not.
    """
    real, fake = pair

    assert fake.tree_sha(spelling) == real.tree_sha(spelling), spelling


@pytest.mark.parametrize("spelling", SPELLINGS)
def test_they_read_the_same_subject(
    pair: tuple[GitRepoQuery, FakeRepoQuery], spelling: str
) -> None:
    real, fake = pair

    assert fake.subject(spelling) == real.subject(spelling), spelling


def test_they_agree_about_ancestry_for_every_pair_of_commits(
    pair: tuple[GitRepoQuery, FakeRepoQuery],
) -> None:
    """Every ordered pair, both directions, including each commit against itself.

    The reflexive case is the one worth naming: `git merge-base --is-ancestor X X`
    exits 0, so the fake has to say yes too — and `history-preserved` relies on it
    when a solver reverts without pushing, because `@c3` and `HEAD` are then the
    same commit.
    """
    real, fake = pair
    commits = [commit.sha for commit in _every_commit(real)]

    assert commits
    disagreements = [
        (first.short, second.short, real.is_ancestor(first, second))
        for first in commits
        for second in commits
        if real.is_ancestor(first, second) != fake.is_ancestor(first, second)
    ]

    assert disagreements == []


def test_they_see_the_same_history_reachable_from_a_ref(
    pair: tuple[GitRepoQuery, FakeRepoQuery],
) -> None:
    """The reachable *set*, not the sequence.

    Git orders a log by commit date; the fake walks parents breadth-first. Those
    agree on a linear history and need not agree across the two sides of a merge,
    and no assertion depends on the ordering — `commit_count` counts and
    `linear_history` looks at parent counts. Comparing sequences would be
    asserting an invariant the engine does not need and the fake cannot honour.
    """
    real, fake = pair
    for ref in ("HEAD", "refs/heads/main", "refs/heads/feature/csv-export"):
        assert _shas(fake.log(ref)) == _shas(real.log(ref)), ref


def test_they_agree_about_which_commits_are_merges(
    pair: tuple[GitRepoQuery, FakeRepoQuery],
) -> None:
    """What `linear_history` reads, so a disagreement here would make that
    assertion pass on one implementation and fail on the other.
    """
    real, fake = pair

    assert _merges(fake.log("HEAD")) == _merges(real.log("HEAD"))


@pytest.mark.parametrize("path", PATHS)
def test_they_read_the_same_working_tree_file(
    pair: tuple[GitRepoQuery, FakeRepoQuery], path: str
) -> None:
    real, fake = pair

    assert fake.worktree_file(path) == real.worktree_file(path), path


@pytest.mark.parametrize("path", PATHS)
def test_they_read_the_same_committed_blob(
    pair: tuple[GitRepoQuery, FakeRepoQuery], path: str
) -> None:
    real, fake = pair

    assert fake.read_blob("HEAD", path) == real.read_blob("HEAD", path), path


# --- the suite's own tripwires ----------------------------------------------


def test_the_states_really_do_differ(provision: Provision) -> None:
    """Without this, six parametrized states could all be the pristine fixture and
    every comparison above would still pass — proving conformance in one state and
    reporting it as six.
    """
    seen: dict[str, tuple[object, ...]] = {}
    for name, reach in STATES.items():
        workspace = provision(FLAGSHIP)
        reach(workspace)
        real = query(workspace)
        seen[name] = (
            real.rev_parse("HEAD"),
            real.head_ref(),
            real.status(),
            len(real.log("HEAD")),
        )

    assert len(set(seen.values())) == len(STATES), seen


def test_the_fake_can_disagree(provision: Provision) -> None:
    """The load is not a copy of the answers, so the comparison can fail.

    A conformance suite whose fake was built from the real one's *conclusions*
    would be unfalsifiable. This gives the fake a graph with one parent link
    removed and checks that it then disagrees with git about ancestry — which is
    the property every test above depends on and none of them can establish.
    """
    workspace = provision(FLAGSHIP)
    real = query(workspace)
    commits = list(_every_commit(real))
    head, parent = commits[0].sha, commits[1].sha

    crippled = FakeRepoQuery(
        RepoState(
            commits={
                commit.sha: Commit(
                    sha=commit.sha,
                    tree=commit.tree,
                    subject=commit.subject,
                    parents=() if commit.sha == head else commit.parents,
                )
                for commit in commits
            },
            refs=dict(real.refs()),
            head=real.head_ref(),
        )
    )

    assert real.is_ancestor(parent, head) is True
    assert crippled.is_ancestor(parent, head) is False


def test_an_empty_fake_is_not_mistaken_for_agreement() -> None:
    """A loader that returned nothing would make every comparison above compare
    `None` with `None` and pass. This is the shape of that failure, named.
    """
    empty = FakeRepoQuery(RepoState())

    assert empty.rev_parse("HEAD") is None
    assert empty.log("HEAD") == ()
    assert empty.status() == WorktreeStatus()


def _shas(commits: Iterable[CommitInfo]) -> frozenset[Sha]:
    """The reachable set, for a comparison that does not depend on log ordering."""
    return frozenset(commit.sha for commit in commits)


def _merges(commits: Iterable[CommitInfo]) -> frozenset[Sha]:
    return frozenset(commit.sha for commit in commits if commit.is_merge)
