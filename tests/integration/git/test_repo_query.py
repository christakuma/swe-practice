"""`GitRepoQuery` against real git, in real repositories.

The unit tests for the 20 assertions run against `FakeRepoQuery` and never touch
a disk. These are the other end: proof that the adapter's parsing agrees with
what git actually prints — porcelain v2's four line kinds, a NUL-separated log
format, `symbolic-ref`'s exit code — on both platforms CI runs.

What is deliberately *not* here is a second copy of the conformance suite. That
one proves the two implementations agree with each other; this one proves this
implementation reads git correctly, which is the claim a conformance failure
cannot settle on its own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tests.integration.git.conftest import query, replay

if TYPE_CHECKING:
    from practice.adapters.sandbox import SubprocessWorkspace

# --- revisions --------------------------------------------------------------


def test_it_resolves_every_revision_the_content_library_uses(
    flagship: SubprocessWorkspace,
) -> None:
    """`HEAD`, a short branch name, a full ref and a remote-tracking ref. All four
    appear in a shipped `with:` mapping, so all four have to resolve.
    """
    repo = query(flagship)
    head = repo.rev_parse("HEAD")

    assert head is not None
    assert repo.rev_parse("main") == head
    assert repo.rev_parse("refs/heads/main") == head
    assert repo.rev_parse("refs/remotes/origin/main") == head


def test_it_reports_a_revision_that_does_not_resolve_as_a_miss(
    flagship: SubprocessWorkspace,
) -> None:
    """The §6.5 rule, at the adapter: a missing ref is a clean `None`, never an
    exception. Without `--verify`, `git rev-parse nonsense` exits 0 and prints the
    string back, so this is the test that catches the flag going missing.
    """
    repo = query(flagship)

    assert repo.rev_parse("refs/heads/does-not-exist") is None
    assert repo.rev_parse("nonsense") is None
    assert repo.tree_sha("refs/heads/does-not-exist") is None


def test_it_resolves_the_fixtures_aliases(flagship: SubprocessWorkspace) -> None:
    """The alias map is what makes `@c2` possible, and it comes from the workspace
    rather than from git — the fixture wrote it (§6.1).
    """
    repo = query(flagship)
    aliases = repo.aliases()

    assert set(aliases) == {"c1", "c2", "c3"}
    assert repo.rev_parse("HEAD") == aliases["c3"]
    assert repo.rev_parse("@c3") is None, (
        "`@c2` is assertion syntax only: the domain resolves it through the alias "
        "map before git ever sees the string (PLAN.md 6.5)"
    )


def test_it_resolves_a_tag_to_the_commit_rather_than_the_tag_object(
    flagship: SubprocessWorkspace,
) -> None:
    """An annotated tag is its own object with its own hash. Without the
    `^{commit}` peel, `tag_points_at {name: v1, target: HEAD}` would fail on a
    correct answer, because the two hashes genuinely differ.
    """
    replay(flagship, "git tag -a v1 -m release\n")
    repo = query(flagship)

    assert repo.rev_parse("refs/tags/v1") == repo.rev_parse("HEAD")
    assert "refs/tags/v1" in repo.refs()


# --- trees ------------------------------------------------------------------


def test_a_revert_restores_the_tree_it_undid(flagship: SubprocessWorkspace) -> None:
    """The §6.6 finding, as a test on the adapter that has to see it: the tree is
    byte-identical while the commit is not. If `tree_sha` returned the commit hash
    instead, `content-restored` would fail every correct answer.
    """
    repo_before = query(flagship)
    original = repo_before.tree_sha(repo_before.aliases()["c2"].value)

    replay(flagship, "git revert --no-edit HEAD\n")
    repo = query(flagship)

    assert original is not None
    assert repo.tree_sha("HEAD") == original
    assert repo.rev_parse("HEAD") != repo.aliases()["c2"]


def test_it_reads_a_committed_blob(flagship: SubprocessWorkspace) -> None:
    repo = query(flagship)

    assert repo.read_blob("HEAD", "build.sh") is not None
    assert repo.read_blob("HEAD", "no-such-file.txt") is None


def test_it_reads_a_working_tree_file_including_an_untracked_one(
    flagship: SubprocessWorkspace,
) -> None:
    """Untracked matters: `file_exists` is for a file a solver wrote, which by
    definition git knows nothing about yet.
    """
    replay(flagship, 'write notes.md "a scratch file"\n')
    repo = query(flagship)

    assert repo.worktree_file("notes.md") == "a scratch file\n"
    assert repo.worktree_file("no-such-file.txt") is None


def test_a_path_that_escapes_the_repository_reads_as_absent(
    flagship: SubprocessWorkspace,
) -> None:
    """An authoring mistake, and its useful report is `<no such file>` in the
    verdict rather than a `WorkspacePathError` traceback (§6.5).
    """
    assert query(flagship).worktree_file("../../.gitconfig") is None


# --- ancestry and history ---------------------------------------------------


def test_it_agrees_with_git_about_ancestry(flagship: SubprocessWorkspace) -> None:
    repo = query(flagship)
    c1 = repo.aliases().get("c1")
    c3 = repo.aliases().get("c3")

    assert c1 is not None
    assert c3 is not None
    assert repo.is_ancestor(c1, c3) is True
    assert repo.is_ancestor(c3, c1) is False
    assert repo.is_ancestor(c3, c3) is True


def test_a_reset_hard_takes_a_commit_out_of_the_branchs_ancestry(
    flagship: SubprocessWorkspace,
) -> None:
    """The contrast that is the product working, at the lowest level it is visible:
    `reset --hard` leaves the same tree and a different ancestry.
    """
    before = query(flagship)
    c3 = before.aliases().get("c3")
    c2_tree = before.tree_sha(before.aliases()["c2"].value)

    replay(flagship, "git reset --hard HEAD~1\n")
    repo = query(flagship)
    head = repo.rev_parse("HEAD")

    assert c3 is not None
    assert head is not None
    assert repo.tree_sha("HEAD") == c2_tree
    assert repo.is_ancestor(c3, head) is False


def test_it_reads_a_log_with_the_fields_the_assertions_need(
    flagship: SubprocessWorkspace,
) -> None:
    repo = query(flagship)
    commits = repo.log("HEAD")

    assert len(commits) == 3
    assert commits[0].sha == repo.rev_parse("HEAD")
    assert commits[0].tree == repo.tree_sha("HEAD")
    assert commits[0].parents == (commits[1].sha,)
    assert commits[-1].parents == ()
    assert all(not commit.is_merge for commit in commits)


def test_it_names_a_merge_as_one(flagship: SubprocessWorkspace) -> None:
    """What `linear_history` reads. A merge is a parent count and nothing else —
    the message says nothing reliable about it.
    """
    replay(
        flagship,
        "git checkout -b side HEAD~2\n"
        'write side.txt "from the side branch"\n'
        "git add side.txt\n"
        "git commit -m side-work\n"
        "git checkout main\n"
        "git merge --no-ff --no-edit side\n",
    )
    repo = query(flagship)
    commits = repo.log("HEAD")

    assert commits[0].is_merge is True
    assert len(commits[0].parents) == 2


def test_a_log_of_a_revision_that_does_not_resolve_is_empty(
    flagship: SubprocessWorkspace,
) -> None:
    assert query(flagship).log("refs/heads/gone") == ()


def test_it_reads_a_subject_including_one_with_awkward_characters(
    flagship: SubprocessWorkspace,
) -> None:
    """The reason the log format is NUL-separated. A subject may contain a tab, a
    colon or a dash, so any printable delimiter is one a fixture author can break
    by accident.

    A pipe would be the sharpest example and cannot be typed here: the command
    policy rejects it as a shell metacharacter before anything runs. That is not a
    defence, though -- a fixture is trusted code and gets a real shell, so a
    fixture author can commit whatever subject they like.
    """
    subject = "fix: a\tb - and a dash"
    replay(
        flagship,
        f"write awkward.txt \"x\"\ngit add awkward.txt\ngit commit -m '{subject}'\n",
    )
    repo = query(flagship)

    assert repo.subject("HEAD") == subject
    assert repo.subject("refs/heads/gone") is None


# --- refs and HEAD ----------------------------------------------------------


def test_it_lists_refs_by_full_name(flagship: SubprocessWorkspace) -> None:
    """Full names, because `branch_exists {name: main}` and `tag_exists
    {name: main}` have to be able to disagree.
    """
    refs = query(flagship).refs()

    assert "refs/heads/main" in refs
    assert "refs/remotes/origin/main" in refs
    assert not any(name == "main" for name in refs)


def test_it_knows_which_branch_head_is_on(flagship: SubprocessWorkspace) -> None:
    assert query(flagship).head_ref() == "refs/heads/main"


def test_it_knows_a_detached_head_even_on_a_branch_tip(
    flagship: SubprocessWorkspace,
) -> None:
    """The case no comparison of hashes can detect, and the exact state
    `naive-detached-checkout.cmds` ends in.
    """
    head = query(flagship).rev_parse("HEAD")
    assert head is not None
    replay(flagship, f"git checkout {head.value}\n")
    repo = query(flagship)

    assert repo.head_ref() is None
    assert repo.rev_parse("HEAD") == head
    assert repo.refs()["refs/heads/main"] == head


# --- the worktree and the index --------------------------------------------


def test_a_fresh_fixture_is_clean(flagship: SubprocessWorkspace) -> None:
    status = query(flagship).status()

    assert status.is_clean is True
    assert status.is_pristine is True


def test_it_separates_staged_from_unstaged_from_untracked(
    flagship: SubprocessWorkspace,
) -> None:
    """Porcelain v2's whole reason for being here: v1 overloads one column for the
    index and the worktree, and `index_staged` has to be able to tell them apart.
    """
    replay(
        flagship,
        'write staged.txt "indexed"\n'
        "git add staged.txt\n"
        'write parser.py "modified but not staged"\n'
        'write scratch.txt "never added"\n',
    )
    status = query(flagship).status()

    assert "staged.txt" in status.staged
    assert "parser.py" in status.unstaged
    assert "scratch.txt" in status.untracked
    assert status.unmerged == frozenset()
    assert status.is_clean is False


def test_an_untracked_file_alone_leaves_the_worktree_clean(
    flagship: SubprocessWorkspace,
) -> None:
    """The §6.5 default, end to end: a scratch file a solver created while poking
    around does not fail them.
    """
    replay(flagship, 'write notes.md "poking around"\n')
    status = query(flagship).status()

    assert status.is_clean is True
    assert status.is_pristine is False


def test_it_reports_unmerged_paths_during_a_conflict(
    flagship: SubprocessWorkspace,
) -> None:
    """A `u` line in porcelain v2, which v1 spells as a two-character code that
    has to be special-cased. `unmerged_paths_empty` is a separate assertion from
    `worktree_clean` only because this distinction survives parsing.
    """
    replay(
        flagship,
        "git checkout -b side HEAD~1\n"
        'write parser.py "the side branch version"\n'
        "git add parser.py\n"
        "git commit -m side-change\n"
        "git checkout main\n"
        "git merge side\n",
    )
    status = query(flagship).status()

    assert "parser.py" in status.unmerged
    assert status.is_clean is False


def test_it_reports_a_renames_new_path_and_not_its_old_one(
    flagship: SubprocessWorkspace,
) -> None:
    """A `2` line carries both paths separated by a tab. Only the new one is a
    path an assertion can usefully be written about — the old one is a file the
    solver correctly got rid of.
    """
    replay(flagship, "git mv parser.py renamed.py\n")
    status = query(flagship).status()

    assert "renamed.py" in status.staged
    assert "parser.py" not in status.staged


# --- recovery surfaces ------------------------------------------------------


def test_it_recovers_a_commit_no_ref_points_at(
    recovery: SubprocessWorkspace,
) -> None:
    """The premise of the exercise, at the adapter: a commit the reflog remembers
    is still resolvable and still has ancestry, even though `log` cannot see it
    from any branch.
    """
    repo = query(recovery)
    lost = repo.rev_parse("HEAD@{3}")
    branch = repo.rev_parse("refs/heads/feature/csv-export")

    assert lost is not None
    assert branch is not None
    assert lost != branch
    assert repo.is_ancestor(branch, lost) is True
    assert lost not in {commit.sha for commit in repo.log("refs/heads/main")}


def test_it_lists_stashes_and_reports_none_as_empty(
    flagship: SubprocessWorkspace,
) -> None:
    """`git stash list` exits 0 on a repository with no stash, so there is no
    missing-ref case — which is worth a test, because the opposite assumption
    would make `stash_count {equals: 0}` unsatisfiable.
    """
    assert query(flagship).stash_list() == ()

    replay(
        flagship,
        'write parser.py "work in progress"\ngit stash push -m wip\n',
    )

    assert len(query(flagship).stash_list()) == 1


# --- the snapshot and caching ----------------------------------------------


def test_the_snapshot_records_the_refs_the_fixture_left(
    flagship: SubprocessWorkspace,
) -> None:
    """What `ref_unchanged {since: fixture}` compares against. It has to keep the
    old value after a ref moves, or the assertion is unfailable.
    """
    main_before = query(flagship).snapshot()["refs/heads/main"]

    replay(flagship, "git reset --hard HEAD~1\n")
    repo = query(flagship)

    assert repo.snapshot()["refs/heads/main"] == main_before
    assert repo.rev_parse("refs/heads/main") != main_before


def test_it_answers_the_same_question_from_its_cache(
    flagship: SubprocessWorkspace,
) -> None:
    """Six checks on one exercise ask `status()` between them, and a git process
    on Windows is the slowest thing in the system.

    Object identity is the whole assertion, and it is enough: `_parse_status`
    builds a fresh `WorktreeStatus` every time it runs, so the same object coming
    back twice can only have come from the cache. Counting processes would need
    instrumentation on `SubprocessWorkspace` that exists for no other reason.

    The cache is per instance and the instance is per grading pass, so there is no
    staleness window -- nothing runs a command between two assertions. An instance
    kept across a solver's commands would be wrong, which is why the factory is a
    call and not a singleton.
    """
    repo = query(flagship)

    assert repo.status() is repo.status()
    assert repo.refs() is repo.refs()
    assert repo.log("HEAD") is repo.log("HEAD")
