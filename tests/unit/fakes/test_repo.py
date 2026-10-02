"""The fake repository's own derivations, tested before anything relies on them.

`FakeRepoQuery` is the oracle for 22 assertion tests, so a bug in it would make
all of them agree with each other and with nothing else. The conformance suite in
`tests/integration/git/` is the other half of this — it proves the fake agrees
with real git — but a conformance failure points at two implementations and says
nothing about which is wrong. These cases pin the fake's answers directly.

Only the *computed* behaviour is covered: revision resolution, ancestry,
reachability, and the refusals. The accessors that hand a dict back need no test,
because there is nothing in them to get wrong.
"""

from __future__ import annotations

import pytest

from practice.domain.ids import Sha
from tests.fakes import a_repo


class TestRevisionResolution:
    """The subset of git's grammar the fake implements (see its module docstring).

    Every spelling here appears in `content/` or in an assertion's `with:`
    mapping, so this is the resolution surface the check engine actually leans on
    rather than a general-purpose parser.
    """

    def test_head_follows_the_branch_it_is_attached_to(self) -> None:
        repo = a_repo()
        first, second = repo.chain("add build script", "add parser")
        repo.branch("main", second).head("refs/heads/main")
        query = repo.build()

        assert query.rev_parse("HEAD") == second
        assert query.rev_parse("main") == second
        assert query.rev_parse("refs/heads/main") == second
        assert first != second

    def test_a_detached_head_resolves_to_the_commit_it_sits_on(self) -> None:
        """And `head_ref` says so, which is the only way `head_detached` can work:
        a detached HEAD on a branch tip is still detached.
        """
        repo = a_repo()
        first, second = repo.chain("add build script", "add parser")
        repo.branch("main", second).detach(first)
        query = repo.build()

        assert query.rev_parse("HEAD") == first
        assert query.head_ref() is None

    @pytest.mark.parametrize(
        ("spelling", "generations"),
        [("HEAD", 0), ("HEAD~1", 1), ("HEAD^", 1), ("HEAD~2", 2), ("HEAD~0", 0)],
    )
    def test_the_ancestry_operators_walk_first_parents(
        self, spelling: str, generations: int
    ) -> None:
        repo = a_repo()
        shas = repo.chain("one", "two", "three")
        repo.branch("main", shas[-1])
        query = repo.build()

        assert query.rev_parse(spelling) == shas[len(shas) - 1 - generations]

    def test_walking_past_the_root_commit_is_a_miss_rather_than_an_error(self) -> None:
        """`HEAD~5` on a three-commit repository is exactly what a counter-example
        looks like after it has gone wrong, and §6.5 says that is a clean failure.
        """
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)

        assert repo.build().rev_parse("HEAD~5") is None

    def test_a_caret_takes_the_nth_parent_of_a_merge(self) -> None:
        repo = a_repo()
        left = repo.commit("left")
        right = repo.commit("right")
        merge = repo.commit("merge", parents=(left, right))
        repo.branch("main", merge)
        query = repo.build()

        assert query.rev_parse("HEAD^1") == left
        assert query.rev_parse("HEAD^2") == right
        assert query.rev_parse("HEAD^3") is None

    def test_a_reflog_selector_reads_the_position_at_that_index(self) -> None:
        """`HEAD@{3}` is the trap in `recover-a-lost-commit`: the reset is not the
        top entry, so an engine that only understood `HEAD@{1}` would grade the
        wrong exercise.
        """
        repo = a_repo()
        shas = repo.chain("skeleton", "exporter", "tests")
        repo.branch("feature/csv-export", shas[0])
        repo.reflog(
            "HEAD",
            [
                (shas[0], "checkout: moving to feature/csv-export"),
                (shas[0], "checkout: moving to main"),
                (shas[0], "reset: moving to HEAD~2"),
                (shas[2], "commit: Add tests for CSV exporter"),
            ],
        )
        query = repo.build()

        assert query.rev_parse("HEAD@{3}") == shas[2]
        assert query.rev_parse("HEAD@{9}") is None

    @pytest.mark.parametrize("length", [4, 7, 12, 40])
    def test_a_hash_resolves_at_every_abbreviation_git_accepts(
        self, length: int
    ) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")

        assert repo.build().rev_parse(first.value[:length]) == first

    def test_an_abbreviation_shorter_than_git_allows_is_a_miss(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")

        assert repo.build().rev_parse(first.value[:3]) is None

    def test_a_short_name_is_searched_in_the_order_git_searches_it(self) -> None:
        """A branch wins over a tag of the same name, which is what git does — and
        why `refs()` is keyed by full name so `branch_exists` and `tag_exists` can
        still disagree.
        """
        repo = a_repo()
        branch_tip, tag_target = repo.chain("one", "two")
        repo.branch("release", branch_tip).tag("release", tag_target)
        query = repo.build()

        assert query.rev_parse("release") == branch_tip
        assert query.rev_parse("refs/tags/release") == tag_target

    @pytest.mark.parametrize(
        "rev", ["", "   ", "nonsense", "refs/heads/gone", "main^{commit}"]
    )
    def test_anything_outside_the_subset_resolves_to_none(self, rev: str) -> None:
        """Including spellings real git accepts. The fake's grammar is a documented
        subset, and the conformance suite is what proves the subset agrees — a
        spelling it does not implement has to miss rather than guess.
        """
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)

        assert repo.build().rev_parse(rev) is None


class TestAncestry:
    def test_a_parent_is_an_ancestor_of_its_child(self) -> None:
        repo = a_repo()
        first, second, third = repo.chain("one", "two", "three")
        query = repo.build()

        assert query.is_ancestor(first, third) is True
        assert query.is_ancestor(third, first) is False
        assert second in (first, second, third)

    def test_a_commit_is_its_own_ancestor_because_git_says_so(self) -> None:
        """`git merge-base --is-ancestor X X` exits 0. Matching it matters: on a
        solution that reverted but did not push, `history-preserved` compares
        `@c3` against a `HEAD` that is the same commit.
        """
        repo = a_repo()
        (first,) = repo.chain("one")

        assert repo.build().is_ancestor(first, first) is True

    def test_a_commit_that_is_not_in_the_repository_is_nobodys_ancestor(self) -> None:
        """Including its own, which is the reflexive case guarded: a hash nothing
        knows about must not pass `is_ancestor` just because it equals itself.
        """
        repo = a_repo()
        (first,) = repo.chain("one")
        unknown = Sha("f" * 40)

        assert repo.build().is_ancestor(unknown, first) is False
        assert repo.build().is_ancestor(unknown, unknown) is False

    def test_both_sides_of_a_merge_are_ancestors_of_it(self) -> None:
        """The case a first-parent-only walk gets wrong, which is why the walk
        follows every parent.
        """
        repo = a_repo()
        left = repo.commit("left")
        right = repo.commit("right")
        merge = repo.commit("merge", parents=(left, right))
        query = repo.build()

        assert query.is_ancestor(left, merge) is True
        assert query.is_ancestor(right, merge) is True

    def test_a_cherry_picked_copy_is_not_an_ancestor_of_the_original(self) -> None:
        """The whole lesson of `naive-cherry-pick.cmds`, as one assertion: the
        files are byte-identical and the subject matches, and the commit is still
        a different commit.
        """
        repo = a_repo()
        original = repo.commit("Add CSV exporter")
        rebuilt = repo.commit(
            "Add CSV exporter", tree=repo.build().tree_sha(original.value)
        )
        repo.branch("feature/csv-export", rebuilt)
        query = repo.build()

        assert query.tree_sha(original.value) == query.tree_sha(rebuilt.value)
        assert query.is_ancestor(original, rebuilt) is False


class TestReachability:
    def test_log_returns_everything_reachable_newest_first(self) -> None:
        repo = a_repo()
        first, second, third = repo.chain("one", "two", "three")
        repo.branch("main", third)
        query = repo.build()

        assert [commit.sha for commit in query.log("HEAD")] == [third, second, first]

    def test_log_sees_both_sides_of_a_merge(self) -> None:
        repo = a_repo()
        base = repo.commit("base")
        left = repo.commit("left", parents=(base,))
        right = repo.commit("right", parents=(base,))
        merge = repo.commit("merge", parents=(left, right))
        repo.branch("main", merge)

        found = {commit.sha for commit in repo.build().log("HEAD")}

        assert found == {base, left, right, merge}

    def test_log_names_a_merge_as_one(self) -> None:
        """What `linear_history` reads. A commit's parent *count* is the only
        reliable signal; nothing in the message says it was a merge.
        """
        repo = a_repo()
        left = repo.commit("left")
        right = repo.commit("right")
        merge = repo.commit("merge", parents=(left, right))
        repo.branch("main", merge)

        commits = repo.build().log("HEAD")

        assert commits[0].is_merge is True
        assert all(not commit.is_merge for commit in commits[1:])

    def test_log_of_a_revision_that_does_not_resolve_is_empty(self) -> None:
        assert a_repo().build().log("refs/heads/gone") == ()
