"""The ten ref, ancestry and history assertions, against the in-memory fake.

No git, no filesystem, milliseconds. That is the return on the `RepoQuery` port
(PLAN.md §6.2), and the conformance suite in `tests/integration/git/` is what makes
it evidence about the real adapter rather than about the fake.

Two things every family's tests cover, because they are where an assertion engine
actually goes wrong: the **missing-revision** case, which must fail cleanly and name
what is absent (§6.5), and the **discriminating** case — the pair of repository
states that a looser assertion would score the same and this one must not.
"""

from __future__ import annotations

from practice.domain.checks.evaluation import MISSING
from tests.fakes import a_repo
from tests.unit.domain.checks.helpers import run


class TestRefPointsAt:
    def test_it_passes_when_both_revisions_are_the_same_commit(self) -> None:
        repo = a_repo()
        first, second = repo.chain("one", "two")
        repo.branch("main", second).remote("main", second)

        report = run(
            repo.build(),
            "ref_points_at",
            ref="refs/remotes/origin/main",
            target="HEAD",
        )

        assert report.passed is True
        assert first != second

    def test_it_fails_when_the_remote_is_behind(self) -> None:
        """`fix-published`, failing: the solver fixed it locally and did not push,
        so the build is still broken for the teammate the exercise is about.
        """
        repo = a_repo()
        first, second = repo.chain("one", "two")
        repo.branch("main", second).remote("main", first)

        report = run(
            repo.build(),
            "ref_points_at",
            ref="refs/remotes/origin/main",
            target="HEAD",
        )

        assert report.passed is False
        assert second.short in (report.expected or "")
        assert first.short in (report.actual or "")

    def test_a_ref_that_does_not_exist_fails_cleanly(self) -> None:
        """The solver deleted the remote. §6.5: a clean failure naming what is
        absent, never a traceback.
        """
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)

        report = run(
            repo.build(),
            "ref_points_at",
            ref="refs/remotes/origin/main",
            target="HEAD",
        )

        assert report.passed is False
        assert MISSING in (report.actual or "")

    def test_a_target_that_does_not_exist_fails_rather_than_matching_nothing(
        self,
    ) -> None:
        """Both sides unresolvable must not compare equal as `None == None`. An
        assertion that passed because neither half existed would be the worst
        available outcome.
        """
        report = run(
            a_repo().build(), "ref_points_at", ref="refs/heads/gone", target="@c9"
        )

        assert report.passed is False


class TestIsAncestor:
    def test_a_revert_leaves_the_bad_commit_reachable(self) -> None:
        """`history-preserved`, passing. This and the next case together are the
        entire argument of PLAN.md §1, in two assertions over two repositories whose
        trees are identical.
        """
        repo = a_repo()
        first, second, third = repo.chain("one", "two", "three")
        revert = repo.commit(
            "Revert three", parents=(third,), tree=repo.build().tree_sha(second.value)
        )
        repo.branch("main", revert)

        report = run(repo.build(), "is_ancestor", ancestor="@c3", descendant="HEAD")

        assert report.passed is True
        assert first != second

    def test_a_reset_hard_does_not(self) -> None:
        """`history-preserved`, failing — with the same tree as the case above.

        The tree is `@c2`'s in both. Any tool grading on file content accepts both,
        and a tool matching command text would have to guess which of two dozen
        correct phrasings to allow. Ancestry is what discriminates.
        """
        repo = a_repo()
        _, second, third = repo.chain("one", "two", "three")
        repo.branch("main", second)
        query = repo.build()

        report = run(query, "is_ancestor", ancestor="@c3", descendant="HEAD")

        assert report.passed is False
        assert report.actual == "not reachable"
        # And the tree is the one a correct revert also lands on, which is the
        # whole reason a content assertion cannot tell these two answers apart.
        assert query.tree_sha("HEAD") == query.tree_sha(second.value)
        assert query.tree_sha("HEAD") != query.tree_sha(third.value)

    def test_a_cherry_picked_copy_is_not_the_commit_it_copied(self) -> None:
        """`originals-recovered`, failing: identical files, identical subject, a
        different commit. Only an ancestry assertion can tell those apart.
        """
        repo = a_repo()
        skeleton = repo.commit("Add project skeleton", alias="c1")
        exporter = repo.commit("Add CSV exporter", parents=(skeleton,), alias="c2")
        rebuilt = repo.commit(
            "Add CSV exporter",
            parents=(skeleton,),
            tree=repo.build().tree_sha(exporter.value),
        )
        repo.branch("feature/csv-export", rebuilt)
        query = repo.build()

        report = run(
            query,
            "is_ancestor",
            ancestor="@c2",
            descendant="refs/heads/feature/csv-export",
        )

        assert report.passed is False
        assert query.tree_sha(exporter.value) == query.tree_sha(rebuilt.value)

    def test_a_commit_is_its_own_ancestor_because_git_says_so(self) -> None:
        """On a solution that reverted and did not push, `@c3` and `HEAD` are the
        same commit. An assertion that called that false would fail a correct answer
        for a reason nobody could guess.
        """
        repo = a_repo()
        first, second, third = repo.chain("one", "two", "three")
        repo.branch("main", third)

        assert (
            run(repo.build(), "is_ancestor", ancestor="@c3", descendant="HEAD").passed
            is True
        )
        assert first != second

    def test_a_missing_revision_names_which_one(self) -> None:
        """Which one is the whole content of the failure: "one of these two does not
        exist" sends a solver looking at both.
        """
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)

        report = run(repo.build(), "is_ancestor", ancestor="@c9", descendant="HEAD")

        assert report.passed is False
        assert "@c9" in (report.actual or "")
        assert "HEAD" not in (report.actual or "")


class TestBranchAndTagExistence:
    def test_a_branch_is_found_by_its_short_name(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("feature/csv-export", first)

        assert (
            run(repo.build(), "branch_exists", name="feature/csv-export").passed is True
        )

    def test_a_branch_is_found_by_its_full_name_too(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)

        assert run(repo.build(), "branch_exists", name="refs/heads/main").passed is True

    def test_a_branch_that_is_not_there_fails(self) -> None:
        report = run(a_repo().build(), "branch_exists", name="main")

        assert report.passed is False
        assert report.actual == "no branch main"

    def test_a_tag_and_a_branch_of_the_same_name_are_different_questions(self) -> None:
        """Which is why `refs()` is keyed by full name. A repository may legally hold
        both, and a short-name map could not tell them apart.
        """
        repo = a_repo()
        first, second = repo.chain("one", "two")
        repo.branch("release", first)
        query = repo.build()

        assert run(query, "branch_exists", name="release").passed is True
        assert run(query, "tag_exists", name="release").passed is False
        assert second != first

    def test_a_tag_points_at_the_commit_it_names(self) -> None:
        repo = a_repo()
        first, second = repo.chain("one", "two")
        repo.branch("main", second).tag("v1", second)
        query = repo.build()

        assert run(query, "tag_points_at", name="v1", target="HEAD").passed is True
        assert (
            run(query, "tag_points_at", name="v1", target=first.value).passed is False
        )

    def test_a_tag_that_is_not_there_fails_cleanly(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)

        report = run(repo.build(), "tag_points_at", name="v1", target="HEAD")

        assert report.passed is False
        assert MISSING in (report.actual or "")


class TestHeadDetached:
    def test_it_passes_when_head_is_not_on_a_branch(self) -> None:
        repo = a_repo()
        first, second = repo.chain("one", "two")
        repo.branch("main", second).detach(first)

        report = run(repo.build(), "head_detached")

        assert report.passed is True
        assert report.actual == "detached"

    def test_it_fails_when_head_is_attached_and_names_the_branch(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("feature/csv-export", first).head("refs/heads/feature/csv-export")

        report = run(repo.build(), "head_detached")

        assert report.passed is False
        assert report.actual == "attached to refs/heads/feature/csv-export"

    def test_a_detached_head_on_a_branch_tip_is_still_detached(self) -> None:
        """The case no comparison of hashes can detect, and the state
        `naive-detached-checkout.cmds` ends in: the files are back, the branch never
        moved, and HEAD is floating.
        """
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first).detach(first)
        query = repo.build()

        assert run(query, "head_detached").passed is True
        assert query.rev_parse("refs/heads/main") == query.rev_parse("HEAD")


class TestRefUnchanged:
    def test_it_passes_when_the_ref_is_where_the_fixture_left_it(self) -> None:
        repo = a_repo()
        first, second = repo.chain("one", "two")
        repo.branch("main", first).branch("feature/csv-export", second)

        assert (
            run(
                repo.build(), "ref_unchanged", ref="refs/heads/main", since="fixture"
            ).passed
            is True
        )

    def test_it_fails_when_the_ref_moved_during_the_attempt(self) -> None:
        """`main-untouched`, failing: resetting `main` onto the feature work fixes
        nothing and breaks a branch that was fine. Every other check in that
        exercise passes on this answer.
        """
        repo = a_repo()
        first, second = repo.chain("one", "two")
        repo.branch("main", first).moved("refs/heads/main", second)
        report = run(
            repo.build(), "ref_unchanged", ref="refs/heads/main", since="fixture"
        )

        assert report.passed is False
        assert first.short in (report.expected or "")
        assert second.short in (report.actual or "")

    def test_a_ref_the_solver_deleted_counts_as_changed(self) -> None:
        repo = a_repo()
        first, second = repo.chain("one", "two")
        repo.branch("main", first).branch("doomed", second)
        query = repo.deleted("refs/heads/doomed").build()

        report = run(query, "ref_unchanged", ref="refs/heads/doomed", since="fixture")

        assert report.passed is False
        assert MISSING in (report.actual or "")
        assert query.snapshot()["refs/heads/doomed"] == second

    def test_a_ref_neither_side_has_ever_had_is_unchanged(self) -> None:
        """Both sides `None`, which compares equal — and is the right answer. A ref
        that never existed and still does not has not changed, and an exercise
        asserting about one has made a different mistake that `branch_exists` names.
        """
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)

        assert (
            run(
                repo.build(), "ref_unchanged", ref="refs/heads/never", since="fixture"
            ).passed
            is True
        )

    def test_since_must_be_fixture_because_nothing_else_is_recorded(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)

        report = run(
            repo.build(),
            "ref_unchanged",
            ref="refs/heads/main",
            since="the-previous-command",
        )

        assert report.passed is False
        assert "misconfigured" in (report.actual or "")


class TestCommitCount:
    def test_it_counts_what_is_reachable(self) -> None:
        repo = a_repo()
        shas = repo.chain("one", "two", "three")
        repo.branch("main", shas[-1])
        query = repo.build()

        assert run(query, "commit_count", equals=3).passed is True
        assert run(query, "commit_count", equals=2).passed is False

    def test_it_counts_both_sides_of_a_merge(self) -> None:
        """ "How many commits are on this branch" is what an author means, and a
        merged side branch's commits are on it — so this is not a first-parent walk.
        """
        repo = a_repo()
        base = repo.commit("base")
        left = repo.commit("left", parents=(base,))
        right = repo.commit("right", parents=(base,))
        merge = repo.commit("merge", parents=(left, right))
        repo.branch("main", merge)

        assert run(repo.build(), "commit_count", equals=4).passed is True

    def test_at_least_and_at_most_both_work(self) -> None:
        repo = a_repo()
        shas = repo.chain("one", "two", "three")
        repo.branch("main", shas[-1])
        query = repo.build()

        assert run(query, "commit_count", at_least=3).passed is True
        assert run(query, "commit_count", at_least=4).passed is False
        assert run(query, "commit_count", at_most=3).passed is True
        assert run(query, "commit_count", at_most=2).passed is False

    def test_it_defaults_to_head(self) -> None:
        repo = a_repo()
        shas = repo.chain("one", "two")
        repo.branch("main", shas[-1])

        assert run(repo.build(), "commit_count", equals=2).passed is True

    def test_a_ref_that_does_not_exist_fails_rather_than_counting_zero(self) -> None:
        """Zero would be a legitimate count and a wrong answer. An exercise asking
        about a branch that is not there needs to hear that, not `0 commits`.
        """
        report = run(a_repo().build(), "commit_count", ref="refs/heads/gone", equals=0)

        assert report.passed is False
        assert MISSING in (report.actual or "")

    def test_one_commit_reads_as_one_commit(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)

        assert run(repo.build(), "commit_count", equals=1).actual == "1 commit"


class TestCommitSubjectMatches:
    def test_it_matches_the_first_line_of_the_message(self) -> None:
        repo = a_repo()
        (first,) = repo.chain('Revert "Rename parse_line to parse"')
        repo.branch("main", first)

        assert (
            run(repo.build(), "commit_subject_matches", pattern=r"^Revert\b").passed
            is True
        )

    def test_a_pattern_that_does_not_match_fails_and_shows_the_subject(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("Rename parse_line to parse")
        repo.branch("main", first)

        report = run(repo.build(), "commit_subject_matches", pattern=r"^Revert\b")

        assert report.passed is False
        assert "Rename parse_line to parse" in (report.actual or "")

    def test_a_ref_that_does_not_resolve_fails_cleanly(self) -> None:
        report = run(
            a_repo().build(),
            "commit_subject_matches",
            ref="refs/heads/gone",
            pattern="anything",
        )

        assert report.passed is False
        assert report.actual == MISSING


class TestLinearHistory:
    def test_a_chain_of_commits_is_linear(self) -> None:
        repo = a_repo()
        shas = repo.chain("one", "two", "three")
        repo.branch("main", shas[-1])

        report = run(repo.build(), "linear_history")

        assert report.passed is True
        assert report.actual == "linear"

    def test_a_merge_commit_is_not_and_the_failure_names_it(self) -> None:
        repo = a_repo()
        left = repo.commit("left")
        right = repo.commit("right")
        merge = repo.commit("merge", parents=(left, right))
        repo.branch("main", merge)

        report = run(repo.build(), "linear_history")

        assert report.passed is False
        assert merge.short in (report.actual or "")

    def test_a_single_root_commit_is_linear(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)

        assert run(repo.build(), "linear_history").passed is True

    def test_a_ref_that_does_not_exist_fails_rather_than_being_vacuously_linear(
        self,
    ) -> None:
        """An empty log holds no merges, so a naive implementation reports a missing
        branch as perfectly linear.
        """
        report = run(a_repo().build(), "linear_history", ref="refs/heads/gone")

        assert report.passed is False
        assert MISSING in (report.actual or "")
