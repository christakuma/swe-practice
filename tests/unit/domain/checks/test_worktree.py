"""The worktree, index and stash assertions.

The family that asks whether a solver finished, plus `stash_count`, which asks
the same question about work parked out of sight.

It covered `reflog_contains` too, including a test asserting that the check was
*vacuously true* on the one exercise that named it — evidence for deleting it,
kept as a test so it could not be forgotten. Phase 11 deleted the assertion and
that test went with it; the reasoning now lives in `domain/checks/recovery.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.fakes import a_repo
from tests.unit.domain.checks.helpers import run

if TYPE_CHECKING:
    from collections.abc import Iterable

    from tests.fakes import FakeRepoQuery


def _repo_with(**status: Iterable[str]) -> FakeRepoQuery:
    """A one-commit repository whose status is whatever the test is about."""
    repo = a_repo()
    (first,) = repo.chain("one")
    repo.branch("main", first)
    repo.status(**status)
    return repo.build()


class TestWorktreeClean:
    def test_a_clean_repository_passes(self) -> None:
        assert run(_repo_with(), "worktree_clean").passed is True

    def test_an_untracked_file_alone_does_not_fail_by_default(self) -> None:
        """PLAN.md §6.5, and it looks like a leniency bug until you remember what
        these exercises teach: a scratch file someone created while poking around
        must not fail them, and poking around is the skill.
        """
        report = run(_repo_with(untracked=["notes.md"]), "worktree_clean")

        assert report.passed is True
        assert "untracked files ignored" in (report.expected or "")

    def test_include_untracked_makes_it_fail(self) -> None:
        """For the exercise whose answer is "and clean up after yourself"."""
        query = _repo_with(untracked=["notes.md"])

        assert run(query, "worktree_clean", include_untracked=True).passed is False
        assert "notes.md" in (
            run(query, "worktree_clean", include_untracked=True).actual or ""
        )

    @pytest.mark.parametrize("kind", ["staged", "unstaged", "unmerged"])
    def test_anything_else_fails_and_says_which_bucket(self, kind: str) -> None:
        """ "The worktree is not clean" is correct and useless. Naming the paths and
        the bucket is the difference between knowing to commit, to discard, or to
        finish a merge.
        """
        report = run(_repo_with(**{kind: ["parser.py"]}), "worktree_clean")

        assert report.passed is False
        assert f"{kind}: parser.py" == report.actual

    def test_several_kinds_at_once_are_all_reported(self) -> None:
        report = run(
            _repo_with(staged=["a.py"], unstaged=["b.py"], unmerged=["c.py"]),
            "worktree_clean",
        )

        assert report.passed is False
        assert report.actual == "staged: a.py; unstaged: b.py; unmerged: c.py"

    def test_untracked_files_are_only_listed_when_they_are_being_graded(self) -> None:
        """A failure report that listed a scratch file under a default
        `worktree_clean` would be pointing at the one thing that is allowed.
        """
        query = _repo_with(staged=["a.py"], untracked=["notes.md"])

        assert "notes.md" not in (run(query, "worktree_clean").actual or "")
        assert "notes.md" in (
            run(query, "worktree_clean", include_untracked=True).actual or ""
        )

    def test_a_flag_that_is_not_a_boolean_is_a_misconfiguration(self) -> None:
        report = run(_repo_with(), "worktree_clean", include_untracked="yes")

        assert report.passed is False
        assert "misconfigured" in (report.actual or "")


class TestIndexStaged:
    def test_it_passes_when_every_named_path_is_staged(self) -> None:
        query = _repo_with(staged=["exporter.py", "test_exporter.py"])

        assert (
            run(query, "index_staged", paths=["exporter.py", "test_exporter.py"]).passed
            is True
        )

    def test_it_needs_every_path_not_any_of_them(self) -> None:
        """An author listing two paths means both. "At least one of these is staged"
        is a claim nobody writes on purpose.
        """
        report = run(
            _repo_with(staged=["exporter.py"]),
            "index_staged",
            paths=["exporter.py", "test_exporter.py"],
        )

        assert report.passed is False
        assert report.actual == "not staged: test_exporter.py"

    def test_an_unstaged_change_to_the_path_does_not_count(self) -> None:
        """The distinction porcelain v2 exists for here: v1 overloads one column for
        the index and the worktree, so this assertion and `worktree_clean` would be
        unable to disagree.
        """
        assert (
            run(
                _repo_with(unstaged=["exporter.py"]),
                "index_staged",
                paths=["exporter.py"],
            ).passed
            is False
        )

    def test_it_takes_a_bare_string_as_one_path(self) -> None:
        assert (
            run(
                _repo_with(staged=["exporter.py"]), "index_staged", paths="exporter.py"
            ).passed
            is True
        )

    def test_it_needs_the_paths_it_is_about(self) -> None:
        report = run(_repo_with(staged=["a.py"]), "index_staged")

        assert report.passed is False
        assert "misconfigured" in (report.actual or "")


class TestUnmergedPathsEmpty:
    def test_a_repository_with_no_conflict_passes(self) -> None:
        report = run(_repo_with(staged=["a.py"]), "unmerged_paths_empty")

        assert report.passed is True
        assert report.actual == "none"

    def test_a_conflict_fails_and_names_the_paths(self) -> None:
        report = run(
            _repo_with(unmerged=["parser.py", "build.sh"]), "unmerged_paths_empty"
        )

        assert report.passed is False
        assert report.actual == "unmerged: build.sh, parser.py"

    def test_it_is_a_different_failure_from_an_unclean_worktree(self) -> None:
        """Which is why it is a separate assertion even though a clean worktree
        implies it: "you have uncommitted changes" and "you are mid-conflict" send a
        solver to different commands.
        """
        query = _repo_with(staged=["a.py"])

        assert run(query, "worktree_clean").passed is False
        assert run(query, "unmerged_paths_empty").passed is True


class TestStashCount:
    def test_no_stash_is_a_real_count_of_zero(self) -> None:
        """`git stash list` exits 0 and prints nothing on a repository with no
        stash, so there is no missing-ref case — and `{equals: 0}` is satisfiable.
        """
        report = run(_repo_with(), "stash_count", equals=0)

        assert report.passed is True
        assert report.actual == "0 stashes"

    def test_it_counts_what_is_there(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first).stash("WIP on main: one", "WIP on main: two")
        query = repo.build()

        assert run(query, "stash_count", equals=2).passed is True
        assert run(query, "stash_count", at_most=1).passed is False
        assert run(query, "stash_count", at_least=2).passed is True

    def test_one_stash_reads_as_one_stash(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first).stash("WIP on main: one")

        assert run(repo.build(), "stash_count", equals=1).actual == "1 stash"

    def test_it_needs_exactly_one_comparison(self) -> None:
        report = run(_repo_with(), "stash_count")

        assert report.passed is False
        assert "exactly one of" in (report.actual or "")
