"""The five tree and content assertions, against the in-memory fake.

The family PLAN.md §6.6 warns hardest about, so the first class below is the
warning written as a test: `tree_equals` passes for a correct revert, for a
`reset --hard` that rewrote published history, *and* for a fix nobody pushed. That
is not a bug in the assertion — it is the reason an exercise needs more than one.
"""

from __future__ import annotations

import pytest

from practice.domain.checks.evaluation import MISSING
from practice.domain.checks.trees import CONFLICT_MARKERS
from tests.fakes import a_repo
from tests.unit.domain.checks.helpers import run


class TestTreeEqualsCannotGradeAnExerciseAlone:
    """The §6.6 finding, as three assertions over three repositories.

    Each one is a different answer to the revert exercise — one right, two wrong —
    and `tree_equals` scores all three identically, because their trees genuinely
    are identical. Any tool grading on file content alone accepts both wrong
    answers.
    """

    @staticmethod
    def _three_commits() -> tuple[object, ...]:
        repo = a_repo()
        shas = repo.chain("skeleton", "working parser", "the bad refactor")
        return (repo, *shas)

    def test_a_correct_revert_passes(self) -> None:
        repo, _, second, third = self._three_commits()
        revert = repo.commit(  # type: ignore[attr-defined]
            'Revert "the bad refactor"',
            parents=(third,),
            tree=repo.build().tree_sha(second.value),  # type: ignore[attr-defined]
        )
        repo.branch("main", revert)  # type: ignore[attr-defined]

        assert (
            run(
                repo.build(),  # type: ignore[attr-defined]
                "tree_equals",
                ref="HEAD",
                target="@c2",
            ).passed
            is True
        )

    def test_a_reset_hard_passes_too(self) -> None:
        repo, _, second, _third = self._three_commits()
        repo.branch("main", second)  # type: ignore[attr-defined]

        assert (
            run(
                repo.build(),  # type: ignore[attr-defined]
                "tree_equals",
                ref="HEAD",
                target="@c2",
            ).passed
            is True
        )

    def test_and_so_does_a_fix_that_was_never_pushed(self) -> None:
        repo, _, second, third = self._three_commits()
        revert = repo.commit(  # type: ignore[attr-defined]
            'Revert "the bad refactor"',
            parents=(third,),
            tree=repo.build().tree_sha(second.value),  # type: ignore[attr-defined]
        )
        repo.branch("main", revert).remote("main", third)  # type: ignore[attr-defined]

        assert (
            run(
                repo.build(),  # type: ignore[attr-defined]
                "tree_equals",
                ref="HEAD",
                target="@c2",
            ).passed
            is True
        )


class TestTreeEquals:
    def test_different_content_fails_and_shows_both_trees(self) -> None:
        repo = a_repo()
        first, second = repo.chain("one", "two")
        repo.branch("main", second)
        query = repo.build()

        report = run(query, "tree_equals", ref="HEAD", target="@c1")

        assert report.passed is False
        assert query.tree_sha(first.value) is not None
        assert MISSING not in (report.actual or "")

    def test_it_defaults_the_ref_to_head(self) -> None:
        repo = a_repo()
        first = repo.commit("one", alias="c1")
        same = repo.commit(
            "two", parents=(first,), tree=repo.build().tree_sha(first.value)
        )
        repo.branch("main", same)

        assert run(repo.build(), "tree_equals", target="@c1").passed is True

    def test_an_alias_is_resolved_before_the_tree_is_looked_up(self) -> None:
        """`tree_sha("@c2")` would hand `@c2` to git, which has never heard of it.
        The alias map is ours and is read first (§6.5).
        """
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)
        query = repo.build()

        assert run(query, "tree_equals", ref="@c1", target="HEAD").passed is True
        assert query.tree_sha("@c1") is None

    @pytest.mark.parametrize(
        ("ref", "target"), [("refs/heads/gone", "HEAD"), ("HEAD", "@c9")]
    )
    def test_a_revision_that_does_not_resolve_fails_cleanly(
        self, ref: str, target: str
    ) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)

        report = run(repo.build(), "tree_equals", ref=ref, target=target)

        assert report.passed is False
        assert MISSING in f"{report.expected} {report.actual}"


class TestFileExists:
    def test_it_sees_a_file_in_the_working_tree(self) -> None:
        """The working tree, not a commit, which is the whole point: an untracked
        file a solver just wrote is one git knows nothing about.
        """
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first).working_file("notes.md", "my notes")

        assert run(repo.build(), "file_exists", path="notes.md").passed is True

    def test_a_file_that_is_not_there_fails(self) -> None:
        report = run(a_repo().build(), "file_exists", path="notes.md")

        assert report.passed is False
        assert MISSING in (report.actual or "")

    def test_negated_it_asserts_the_file_is_gone(self) -> None:
        """Which is the common shape, for an exercise whose answer is removing
        something.
        """
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)

        assert (
            run(repo.build(), "file_exists", path="secrets.env", negated=True).passed
            is True
        )


class TestFileMatches:
    def test_it_matches_the_working_trees_copy(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first).working_file(
            "parser.py", "def parse_line(line):\n    return line\n"
        )

        assert (
            run(
                repo.build(),
                "file_matches",
                path="parser.py",
                pattern=r"def parse_line\b",
            ).passed
            is True
        )

    def test_a_pattern_that_does_not_match_says_how_much_it_read(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first).working_file("parser.py", "def parse(line):\n")

        report = run(
            repo.build(), "file_matches", path="parser.py", pattern=r"def parse_line\b"
        )

        assert report.passed is False
        assert "no match in" in (report.actual or "")

    def test_a_file_that_is_not_there_fails_rather_than_matching_nothing(self) -> None:
        report = run(
            a_repo().build(), "file_matches", path="gone.py", pattern="anything"
        )

        assert report.passed is False
        assert MISSING in (report.actual or "")

    def test_the_working_tree_and_a_commit_are_different_questions(self) -> None:
        """ "You fixed it" and "you committed the fix" are different claims, and an
        exercise about a half-finished fix needs to be able to make one and not the
        other. This is the state a `git checkout <sha> -- .` leaves behind.
        """
        repo = a_repo()
        first = repo.commit(
            "the bad refactor", alias="c1", files={"parser.py": "def parse(x): ...\n"}
        )
        repo.branch("main", first).working_file("parser.py", "def parse_line(x): ...\n")
        query = repo.build()

        assert (
            run(
                query, "file_matches", path="parser.py", pattern=r"def parse_line\b"
            ).passed
            is True
        )
        assert (
            run(
                query,
                "file_at_ref_matches",
                ref="HEAD",
                path="parser.py",
                pattern=r"def parse_line\b",
            ).passed
            is False
        )


class TestFileAtRefMatches:
    def test_it_reads_the_committed_blob(self) -> None:
        repo = a_repo()
        first = repo.commit(
            "working parser",
            alias="c1",
            files={"parser.py": "def parse_line(x): ...\n"},
        )
        repo.branch("main", first)

        assert (
            run(
                repo.build(),
                "file_at_ref_matches",
                ref="@c1",
                path="parser.py",
                pattern=r"def parse_line\b",
            ).passed
            is True
        )

    def test_it_defaults_the_ref_to_head(self) -> None:
        repo = a_repo()
        first = repo.commit("one", files={"README.md": "# invoice-tool\n"})
        repo.branch("main", first)

        assert (
            run(
                repo.build(),
                "file_at_ref_matches",
                path="README.md",
                pattern="invoice-tool",
            ).passed
            is True
        )

    def test_a_ref_that_does_not_resolve_fails_cleanly(self) -> None:
        report = run(
            a_repo().build(),
            "file_at_ref_matches",
            ref="refs/heads/gone",
            path="README.md",
            pattern="anything",
        )

        assert report.passed is False
        assert MISSING in (report.actual or "")

    def test_undecodable_bytes_do_not_raise(self) -> None:
        """A solver can commit any bytes they like, and a `UnicodeDecodeError` from
        inside a grading pass is the traceback §6.5 exists to prevent. Undecodable
        bytes become replacement characters, which no pattern matches by accident.
        """
        repo = a_repo()
        first = repo.commit("add a logo")
        repo.branch("main", first).blob(first, "logo.png", _NOT_TEXT)

        report = run(
            repo.build(), "file_at_ref_matches", path="logo.png", pattern="PNG"
        )

        assert report.passed is True


#: Bytes no encoding accepts, for the test above. The builder takes text
#: everywhere else, because every other blob in the vocabulary is text.
_NOT_TEXT = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0xFF, 0xFE])


class TestNoConflictMarkers:
    def test_a_clean_file_passes(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first).working_file("parser.py", "def parse(x): ...\n")

        report = run(repo.build(), "no_conflict_markers", paths=["parser.py"])

        assert report.passed is True
        assert report.actual == "clean"

    def test_a_file_full_of_markers_fails_and_names_it(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first).working_file(
            "parser.py",
            "<<<<<<< HEAD\ndef parse(x): ...\n=======\ndef parse_line(x): ...\n"
            ">>>>>>> side\n",
        )

        report = run(repo.build(), "no_conflict_markers", paths=["parser.py"])

        assert report.passed is False
        assert "parser.py" in (report.actual or "")

    def test_it_takes_a_bare_string_as_one_path(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first).working_file("parser.py", "clean\n")

        assert (
            run(repo.build(), "no_conflict_markers", paths="parser.py").passed is True
        )

    def test_a_file_that_is_not_there_counts_as_clean(self) -> None:
        """Not a loophole: `file_exists` is the assertion for "the file is present",
        and reporting a missing file as full of conflict markers would be a lie
        about a different problem.
        """
        assert (
            run(a_repo().build(), "no_conflict_markers", paths=["gone.py"]).passed
            is True
        )

    def test_with_a_ref_it_reads_the_committed_copy(self) -> None:
        """A committed conflict is the worse mistake, and the one a solver cannot
        see in `git status`.
        """
        repo = a_repo()
        first = repo.commit(
            "committed the conflict",
            files={"parser.py": "<<<<<<< HEAD\na\n=======\nb\n>>>>>>> side\n"},
        )
        repo.branch("main", first).working_file("parser.py", "resolved\n")
        query = repo.build()

        assert run(query, "no_conflict_markers", paths=["parser.py"]).passed is True
        assert (
            run(query, "no_conflict_markers", paths=["parser.py"], ref="HEAD").passed
            is False
        )

    def test_it_needs_the_paths_it_is_about(self) -> None:
        """Required rather than discovered: `RepoQuery` has no directory listing, and
        inventing one would mean deciding what a check does about `.git/`, about
        untracked files, and about a repository with ten thousand paths.
        """
        report = run(a_repo().build(), "no_conflict_markers")

        assert report.passed is False
        assert "misconfigured" in (report.actual or "")


class TestTheConflictMarkerPattern:
    @pytest.mark.parametrize(
        "line",
        [
            "<<<<<<< HEAD",
            "======= ",
            ">>>>>>> feature/csv-export",
            "<<<<<<<",
            "=======",
        ],
    )
    def test_it_matches_what_git_writes(self, line: str) -> None:
        assert CONFLICT_MARKERS.search(f"a\n{line}\nb\n") is not None

    @pytest.mark.parametrize(
        "line",
        [
            "====",
            "========",
            "Heading\n=======text",
            "a <<<<<<< HEAD",
            "<<<<<< HEAD",
        ],
    )
    def test_it_does_not_match_things_that_merely_look_like_it(self, line: str) -> None:
        """Seven characters exactly, at the start of a line, followed by whitespace
        or nothing. A looser pattern matches the `====` under a reStructuredText
        heading and fails an exercise for writing documentation.
        """
        assert CONFLICT_MARKERS.search(f"a\n{line}\nb\n") is None
