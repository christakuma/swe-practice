"""The four worktree, index, stash and reflog assertions.

The family that asks whether a solver finished, plus the two recovery assertions —
one of which is on probation and says so in its own module.
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


class TestReflogContains:
    """Implemented, and on probation. The module docstring says why: it is either
    vacuously true where the fixture made the entry, or it grades *how* a solver got
    somewhere — which is the thing PLAN.md §1 exists to reject. Deleted rather than
    carried if no Phase 11 exercise needs it.
    """

    @staticmethod
    def _recovery_repo() -> FakeRepoQuery:
        """The recovery scenario's reflog, including the trap: the reset is not the
        top entry, because two branch switches happened after it.
        """
        repo = a_repo()
        skeleton, exporter, tests = repo.chain("skeleton", "exporter", "tests")
        repo.branch("main", skeleton).branch("feature/csv-export", skeleton)
        repo.reflog(
            "HEAD",
            [
                (skeleton, "checkout: moving from main to feature/csv-export"),
                (skeleton, "checkout: moving from feature/csv-export to main"),
                (skeleton, "reset: moving to main"),
                (tests, "commit: Add tests for CSV exporter"),
                (exporter, "commit: Add CSV exporter"),
            ],
        )
        return repo.build()

    def test_it_finds_a_matching_entry_and_reports_its_position(self) -> None:
        """The position, not the hash, because `HEAD@{3}` is the thing a solver can
        type — and reading past the top entry is the lesson.
        """
        report = run(
            self._recovery_repo(), "reflog_contains", ref="HEAD", pattern="^reset:"
        )

        assert report.passed is True
        assert "HEAD@{2}" in (report.actual or "")

    def test_a_pattern_that_matches_nothing_shows_what_was_there(self) -> None:
        report = run(
            self._recovery_repo(), "reflog_contains", ref="HEAD", pattern="^rebase:"
        )

        assert report.passed is False
        assert "no match in 5 entries" in (report.actual or "")

    def test_a_long_reflog_is_truncated_rather_than_dumped(self) -> None:
        """A busy repository's reflog runs to hundreds of entries, and a verdict that
        printed them all would bury every other check.
        """
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first).reflog(
            "HEAD", [(first, f"commit: number {index}") for index in range(12)]
        )

        report = run(repo.build(), "reflog_contains", pattern="^rebase:")

        assert report.passed is False
        assert "+7 more" in (report.actual or "")

    def test_a_ref_with_no_reflog_fails_cleanly(self) -> None:
        """A branch created with `git branch` and never moved has an empty reflog,
        which is an ordinary repository state rather than a fault (§6.5).
        """
        report = run(
            _repo_with(), "reflog_contains", ref="refs/heads/main", pattern="anything"
        )

        assert report.passed is False
        assert report.actual == "refs/heads/main has no reflog"

    def test_it_defaults_to_head(self) -> None:
        assert (
            run(self._recovery_repo(), "reflog_contains", pattern="^commit:").passed
            is True
        )

    def test_it_is_vacuously_true_where_the_fixture_made_the_entry(self) -> None:
        """The probation, as a test. Every attempt at `recover-a-lost-commit` passes
        `reflog_contains {pattern: "^reset:"}` -- including one that never ran a
        single command -- because the *fixture's* `reset --hard` wrote that entry.

        This is not a bug to fix. It is the evidence for deleting the assertion, and
        a test is where that evidence belongs so it cannot be forgotten.
        """
        untouched = self._recovery_repo()

        assert run(untouched, "reflog_contains", pattern="^reset:").passed is True
