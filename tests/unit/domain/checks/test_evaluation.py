"""`Params`, `resolve`, and the dispatcher's three failure modes.

The machinery every assertion shares, tested once here rather than 22 times. What
the per-family modules then test is the assertion's own logic, which is the thing
that differs.
"""

from __future__ import annotations

import pytest

from practice.domain.checks.evaluation import (
    MISSING,
    CheckResult,
    CheckSpecError,
    Params,
    compare,
    describe,
    matcher,
    resolve,
)
from practice.domain.ids import Sha
from practice.domain.verdict import Severity
from tests.fakes import a_repo
from tests.unit.domain.checks.helpers import run


class TestNegation:
    """`not:` is a uniform modifier on every assertion (PLAN.md §6.3), applied in
    exactly one place, so these cases cover all 22 at once.
    """

    def test_it_inverts_the_verdict(self) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first).detach(first)
        query = repo.build()

        assert run(query, "head_detached").passed is True
        assert run(query, "head_detached", negated=True).passed is False

    def test_it_rewrites_the_expectation_so_the_report_reads_correctly(self) -> None:
        """The reason `expected` is a noun phrase. A failing `not: true` check that
        still said "expected a detached HEAD" would be telling the solver to do the
        opposite of what the exercise wants.
        """
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)

        report = run(repo.build(), "head_detached", negated=True)

        assert report.passed is True
        assert report.expected == "not a detached HEAD"

    def test_it_leaves_what_was_actually_found_alone(self) -> None:
        """What was found is what was found; only the judgement about it inverts."""
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)
        query = repo.build()

        plain = run(query, "head_detached")
        negated = run(query, "head_detached", negated=True)

        assert plain.actual == negated.actual == "attached to refs/heads/main"

    def test_negating_twice_returns_the_original_verdict(self) -> None:
        result = CheckResult(passed=True, expected="a thing", actual="the thing")

        assert result.negate().negate().passed is result.passed


class TestTheAuthorsWords:
    def test_every_report_carries_the_label_severity_and_explanation(self) -> None:
        """Through `CheckReport.from_spec`, so no assertion can forget to and none
        has to know how.
        """
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)

        report = run(
            repo.build(),
            "head_detached",
            check_id="on-a-branch",
            severity=Severity.ADVISORY,
        )

        assert report.check_id == "on-a-branch"
        assert report.label == "The thing the author said."
        assert report.severity is Severity.ADVISORY
        assert report.explanation == "Why this matters."


class TestAMisconfiguredCheck:
    """An authoring bug fails cleanly, for the reason §6.5 gives about a missing
    ref: the person reading the verdict is a solver who cannot fix the exercise.
    CI's graded replay is where the same condition becomes a build failure.
    """

    def test_a_missing_parameter_is_a_failing_report_not_a_traceback(self) -> None:
        report = run(a_repo().build(), "is_ancestor")

        assert report.passed is False
        assert "misconfigured" in (report.actual or "")
        assert "ancestor" in (report.actual or "")

    def test_a_parameter_of_the_wrong_type_is_the_same(self) -> None:
        report = run(a_repo().build(), "commit_count", ref="HEAD", equals="three")

        assert report.passed is False
        assert "misconfigured" in (report.actual or "")

    def test_a_pattern_that_will_not_compile_is_the_same(self) -> None:
        report = run(a_repo().build(), "commit_subject_matches", pattern="([")

        assert report.passed is False
        assert "regular expression" in (report.actual or "")

    def test_an_advisory_misconfiguration_stays_advisory(self) -> None:
        """So a broken advisory check cannot fail an attempt that was correct. The
        severity is the author's and the dispatcher never overrides it.
        """
        report = run(
            a_repo().build(),
            "is_ancestor",
            severity=Severity.ADVISORY,
        )

        assert report.passed is False
        assert report.is_blocking is False


class TestAnAssertionThatHasNotLandedYet:
    def test_it_reports_rather_than_raising(self) -> None:
        """A within-phase scaffold: the schema accepts the whole vocabulary while
        the table holds however much of it is implemented. Gone by the end of
        Phase 5, and worth a test until then — the alternative is a `KeyError`
        in front of a solver.
        """
        report = run(a_repo().build(), "command_used", pattern="push")

        assert report.passed is False
        assert "not implemented yet" in (report.actual or "")


class TestResolve:
    def test_an_alias_is_resolved_from_the_fixtures_map(self) -> None:
        repo = a_repo()
        first, second = repo.chain("one", "two")
        repo.branch("main", second)
        query = repo.build()

        assert resolve(query, "@c1") == first
        assert resolve(query, "@c2") == second

    def test_an_alias_is_resolved_before_git_is_asked(self) -> None:
        """The §6.5 ordering, as a test. `@c2` can never collide with git's own `@`
        syntax because git is never shown it — and the fake proves that by having
        no revision grammar that would accept it.
        """
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)
        query = repo.build()

        assert resolve(query, "@c1") == first
        assert query.rev_parse("@c1") is None

    def test_an_alias_the_fixture_never_recorded_is_a_miss(self) -> None:
        """Not an error. A real authoring mistake, and the content suite is what
        catches it — by checking every alias a check names against what the fixture
        actually produced.
        """
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)

        assert resolve(repo.build(), "@c9") is None

    @pytest.mark.parametrize("rev", ["HEAD", "main", "refs/heads/main"])
    def test_anything_else_goes_to_the_repository(self, rev: str) -> None:
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first)

        assert resolve(repo.build(), rev) == first

    @pytest.mark.parametrize("rev", ["@", "@1c", "@c 2", "@-c1", "HEAD@{1}"])
    def test_what_is_not_alias_syntax_is_not_treated_as_one(self, rev: str) -> None:
        """`HEAD@{1}` is the case that matters: it is git's syntax and must reach
        git. The alias pattern requires the `@` to start the string and be followed
        by a letter, which is what keeps the two apart.
        """
        repo = a_repo()
        (first,) = repo.chain("one")
        repo.branch("main", first).reflog("HEAD", [(first, "commit: one")])

        assert resolve(repo.build(), rev) != Sha("c" + "0" * 38 + "9")


class TestDescribe:
    def test_a_hash_is_abbreviated_the_way_git_abbreviates_it(self) -> None:
        assert describe(Sha("a" * 40)) == "a" * 7

    def test_a_revision_that_is_not_there_has_one_spelling(self) -> None:
        """One string, used everywhere, so a verdict never has two spellings of the
        same situation.
        """
        assert describe(None) == MISSING


class TestParams:
    def test_text_accepts_a_string_and_an_explicit_default(self) -> None:
        params = Params(assertion="tree_equals", values={"ref": "HEAD"})

        assert params.text("ref") == "HEAD"
        assert params.text("target", default="HEAD") == "HEAD"

    @pytest.mark.parametrize("value", ["", "   "])
    def test_text_refuses_an_empty_string(self, value: str) -> None:
        """A present-but-empty `ref:` is a different mistake from a missing one and
        would otherwise be handed to git as the empty revision.
        """
        params = Params(assertion="tree_equals", values={"ref": value})

        with pytest.raises(CheckSpecError, match="is empty"):
            params.text("ref")

    def test_text_refuses_a_non_string(self) -> None:
        params = Params(assertion="tree_equals", values={"ref": 3})

        with pytest.raises(CheckSpecError, match="must be a string"):
            params.text("ref")

    def test_a_missing_parameter_with_no_default_is_refused(self) -> None:
        """Rather than defaulted. `is_ancestor` with no `ancestor:` has nothing to
        compare, and the only honest answers are "refuse" or "silently grade
        something else".
        """
        params = Params(assertion="is_ancestor", values={})

        with pytest.raises(CheckSpecError, match="missing required parameter"):
            params.text("ancestor")

    def test_integer_accepts_an_integer(self) -> None:
        params = Params(assertion="commit_count", values={"equals": 3})

        assert params.integer("equals") == 3

    def test_integer_refuses_a_bool_even_though_python_says_it_is_one(self) -> None:
        """`commit_count {equals: true}` is a typo, not a count of one — and YAML
        makes it an easy one to make.
        """
        params = Params(assertion="commit_count", values={"equals": True})

        with pytest.raises(CheckSpecError, match="must be an integer"):
            params.integer("equals")

    def test_flag_always_has_a_default(self) -> None:
        params = Params(assertion="worktree_clean", values={})

        assert params.flag("include_untracked", default=False) is False
        assert params.flag("include_untracked", default=True) is True

    def test_flag_refuses_a_non_boolean(self) -> None:
        params = Params(assertion="worktree_clean", values={"include_untracked": "yes"})

        with pytest.raises(CheckSpecError, match="true or false"):
            params.flag("include_untracked", default=False)

    def test_paths_accepts_a_list(self) -> None:
        params = Params(assertion="index_staged", values={"paths": ("a.py", "b/c.py")})

        assert params.paths("paths") == ("a.py", "b/c.py")

    def test_paths_accepts_a_bare_string_as_a_list_of_one(self) -> None:
        """YAML makes `paths: src/a.py` and `paths: [src/a.py]` look equally
        correct, and refusing the first would be refusing an exercise that is
        already unambiguous.
        """
        params = Params(assertion="index_staged", values={"paths": "a.py"})

        assert params.paths("paths") == ("a.py",)

    @pytest.mark.parametrize("value", [(), ("a.py", ""), ("a.py", 3), 7])
    def test_paths_refuses_anything_that_is_not_one(self, value: object) -> None:
        params = Params(
            assertion="index_staged",
            values={"paths": value},  # type: ignore[dict-item]
        )

        with pytest.raises(CheckSpecError):
            params.paths("paths")

    @pytest.mark.parametrize(
        ("key", "wanted"), [("equals", 3), ("at_least", 1), ("at_most", 9)]
    )
    def test_comparison_returns_the_one_key_present(
        self, key: str, wanted: int
    ) -> None:
        params = Params(assertion="commit_count", values={key: wanted})

        assert params.comparison() == (key, wanted)

    def test_no_comparison_at_all_is_refused(self) -> None:
        """A `commit_count` with no comparison would pass unconditionally, which is
        the vacuous-check failure §5.4 is about.
        """
        params = Params(assertion="commit_count", values={"ref": "HEAD"})

        with pytest.raises(CheckSpecError, match="exactly one of"):
            params.comparison()

    def test_two_comparisons_are_refused(self) -> None:
        """An author who wrote both meant one of them and would never find out
        which was used.
        """
        params = Params(assertion="commit_count", values={"equals": 3, "at_least": 1})

        with pytest.raises(CheckSpecError, match="exactly one of"):
            params.comparison()

    def test_the_error_names_the_assertion_it_came_from(self) -> None:
        """A verdict showing six checks needs to say which one is broken."""
        params = Params(assertion="tree_equals", values={})

        with pytest.raises(CheckSpecError, match="tree_equals"):
            params.text("target")


class TestCompare:
    @pytest.mark.parametrize(
        ("operator", "actual", "wanted", "expected"),
        [
            ("equals", 3, 3, True),
            ("equals", 3, 4, False),
            ("at_least", 3, 3, True),
            ("at_least", 4, 3, True),
            ("at_least", 2, 3, False),
            ("at_most", 3, 3, True),
            ("at_most", 2, 3, True),
            ("at_most", 4, 3, False),
        ],
    )
    def test_each_operator_means_what_it_says(
        self, operator: str, actual: int, wanted: int, expected: bool
    ) -> None:
        assert compare(operator, actual, wanted) is expected

    def test_an_operator_with_no_rule_is_a_keyerror_rather_than_a_pass(self) -> None:
        """A mapping rather than a chain of branches, so an operator added to the
        vocabulary without a rule here fails in the test that adds it.
        """
        with pytest.raises(KeyError):
            compare("roughly", 3, 3)


class TestMatcher:
    def test_it_compiles_the_authors_pattern(self) -> None:
        params = Params(assertion="command_used", values={"pattern": "push.*force"})

        assert matcher(params).search("git push --force origin main") is not None

    def test_it_is_unanchored_because_the_content_relies_on_that(self) -> None:
        params = Params(
            assertion="command_used",
            values={"pattern": r"push\b.*(--force|--force-with-lease|-f)\b"},
        )

        assert matcher(params).search("git push --force origin main") is not None

    def test_a_pattern_that_will_not_compile_is_a_check_spec_error(self) -> None:
        params = Params(assertion="command_used", values={"pattern": "([unclosed"})

        with pytest.raises(CheckSpecError, match="regular expression"):
            matcher(params)
