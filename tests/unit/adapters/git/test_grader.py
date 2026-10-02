"""`ScenarioGrader`, against the in-memory fake. No git, no filesystem.

The grader is an adapter and this is a unit test, which is only possible because
the `RepoQuery` factory is injected: the interesting part of the class is the
assembly — every check runs, in the author's order, into a `Verdict` whose outcome
is derived — and none of that needs a repository on disk.

The exercises here are built out of real `CheckSpec`s, so the §6.6 contrast is
expressible end to end: the last class below grades the same two answers the flagship
scenario grades and asserts they come apart on exactly one check.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.git import ScenarioGrader, ScenarioGraderError
from practice.domain.exercise import (
    CheckSpec,
    Difficulty,
    Exercise,
    ExerciseKind,
    GitScenarioSpec,
    Hint,
)
from practice.domain.ids import ExerciseId, tag
from practice.domain.verdict import Outcome, Severity
from tests.fakes import FakeWorkspace, a_kata, a_repo
from tests.unit.domain.checks.helpers import an_attempt

if TYPE_CHECKING:
    from practice.domain.ids import Sha
    from practice.domain.ports import RepoQuery, Workspace
    from tests.fakes import RepoBuilder


def a_check(
    check_id: str,
    assertion: str,
    *,
    severity: Severity = Severity.REQUIRED,
    negated: bool = False,
    **params: object,
) -> CheckSpec:
    return CheckSpec(
        id=check_id,
        label=f"The author's sentence about {check_id}.",
        severity=severity,
        assertion=assertion,
        params=params,  # type: ignore[arg-type]
        negated=negated,
        explanation=f"Why {check_id} matters.",
    )


def a_scenario(*checks: CheckSpec) -> Exercise:
    """A git scenario carrying exactly the checks a test is about."""
    return Exercise(
        id=ExerciseId("git/revert-a-pushed-commit"),
        kind=ExerciseKind.GIT_SCENARIO,
        title="Undo a commit that is already on origin",
        prompt="Get main working again, without rewriting published history.",
        difficulty=Difficulty.MEDIUM,
        tags=(tag("history"),),
        estimated_minutes=10,
        hints=(Hint("What does your teammate already have?"),),
        notes="Why revert and not reset.",
        spec=GitScenarioSpec(
            fixture="fixture.sh",
            reference="solution.cmds",
            checks=checks,
            allowed_commands=frozenset({"git", "cat"}),
        ),
    )


def grader_over(query: RepoQuery) -> ScenarioGrader:
    """A grader that hands out the fake, ignoring the workspace it is given.

    Which is the point of the injected factory: the assembly does not care where a
    `RepoQuery` comes from, so proving it right costs a millisecond.
    """

    def factory(workspace: Workspace) -> RepoQuery:
        del workspace
        return query

    return ScenarioGrader(factory)


def _three_commits() -> tuple[RepoBuilder, Sha, Sha, Sha]:
    """The flagship fixture's shape: a skeleton, a parser, and the bad refactor."""
    repo = a_repo()
    first, second, third = repo.chain("skeleton", "working parser", "bad refactor")
    return repo, first, second, third


class TestAssembly:
    def test_every_check_runs_even_after_one_fails(self) -> None:
        """The whole argument of §6.6: a wrong answer passes some checks and fails
        others, and *which* ones is the feedback. "Failed at check 3" is not.
        """
        repo, _, _, third = _three_commits()
        repo.branch("main", third)
        grader = grader_over(repo.build())
        exercise = a_scenario(
            a_check("will-fail", "branch_exists", name="nope"),
            a_check("will-pass", "head_detached", negated=True),
            a_check("will-fail-too", "tag_exists", name="v1"),
        )

        verdict = grader.grade(exercise, FakeWorkspace(), an_attempt())

        assert len(verdict.reports) == 3
        assert [report.passed for report in verdict.reports] == [False, True, False]

    def test_reports_come_back_in_the_order_the_exercise_declares_them(self) -> None:
        """So two runs of the same answer read the same way down the page, and an
        author can put the thing they most want read first.
        """
        repo, _, _, third = _three_commits()
        repo.branch("main", third)
        exercise = a_scenario(
            a_check("first", "head_detached", negated=True),
            a_check("second", "linear_history"),
            a_check("third", "commit_count", equals=3),
        )

        verdict = grader_over(repo.build()).grade(
            exercise, FakeWorkspace(), an_attempt()
        )

        assert [report.check_id for report in verdict.reports] == [
            "first",
            "second",
            "third",
        ]

    def test_the_outcome_is_derived_from_the_reports(self) -> None:
        repo, _, _, third = _three_commits()
        repo.branch("main", third)
        grader = grader_over(repo.build())

        assert (
            grader.grade(
                a_scenario(a_check("ok", "linear_history")),
                FakeWorkspace(),
                an_attempt(),
            ).outcome
            is Outcome.PASS
        )
        assert (
            grader.grade(
                a_scenario(a_check("bad", "head_detached")),
                FakeWorkspace(),
                an_attempt(),
            ).outcome
            is Outcome.FAIL
        )

    def test_a_failing_advisory_is_a_pass_with_advisories(self) -> None:
        """§4.4's feature, through the grader: you achieved the goal, and here is the
        cost. An advisory that failed the attempt would make the distinction
        pointless.
        """
        repo, _, _, third = _three_commits()
        repo.branch("main", third)
        attempt = an_attempt([["git", "push", "--force", "origin", "main"]])
        exercise = a_scenario(
            a_check("content", "linear_history"),
            a_check(
                "no-force-push",
                "command_used",
                severity=Severity.ADVISORY,
                negated=True,
                pattern=r"push\b.*--force\b",
            ),
        )

        verdict = grader_over(repo.build()).grade(exercise, FakeWorkspace(), attempt)

        assert verdict.outcome is Outcome.PASS_WITH_ADVISORIES
        assert verdict.passed is True
        assert [report.check_id for report in verdict.advisories] == ["no-force-push"]

    def test_the_authors_words_survive_the_round_trip(self) -> None:
        repo, _, _, third = _three_commits()
        repo.branch("main", third)
        exercise = a_scenario(a_check("history-preserved", "head_detached"))

        report = (
            grader_over(repo.build())
            .grade(exercise, FakeWorkspace(), an_attempt())
            .reports[0]
        )

        assert report.label == "The author's sentence about history-preserved."
        assert report.explanation == "Why history-preserved matters."

    def test_a_misconfigured_check_fails_without_taking_the_pass_down_with_it(
        self,
    ) -> None:
        """One broken check must not cost the verdict its other five. The dispatcher
        catches `CheckSpecError` per check, so a `with:` typo costs that check and
        nothing else.
        """
        repo, _, _, third = _three_commits()
        repo.branch("main", third)
        exercise = a_scenario(
            a_check("broken", "is_ancestor"),
            a_check("fine", "linear_history"),
        )

        verdict = grader_over(repo.build()).grade(
            exercise, FakeWorkspace(), an_attempt()
        )

        assert verdict.outcome is Outcome.FAIL
        assert [report.passed for report in verdict.reports] == [False, True]
        assert "misconfigured" in (verdict.reports[0].actual or "")


class TestItRefusesWhatItCannotGrade:
    def test_a_kata_is_refused_rather_than_graded_badly(self) -> None:
        """The kind registry should have refused first. This is the second gate, for
        the same reason `SubprocessWorkspace` re-checks the policy its caller
        already applied.
        """
        grader = grader_over(a_repo().build())

        with pytest.raises(ScenarioGraderError, match="does not know how to grade"):
            grader.grade(a_kata(), FakeWorkspace(), an_attempt())

    def test_it_defaults_to_the_real_repo_query(self) -> None:
        """The factory is optional, so the composition root reads as one line. A
        `ScenarioGrader()` with no argument has to be the production one.
        """
        assert ScenarioGrader()._query_for is not None


class TestTheContrastThatIsTheProductWorking:
    """PLAN.md §6.6's table, as two graded verdicts over the exercise's own checks.

    The trees are identical in both. Any tool grading on file content accepts both,
    and a tool matching command text would have to guess which of two dozen correct
    phrasings to allow. One check tells them apart, and it is an ancestry check.
    """

    @staticmethod
    def _flagship_checks() -> tuple[CheckSpec, ...]:
        return (
            a_check("content-restored", "tree_equals", ref="HEAD", target="@c2"),
            a_check("clean-worktree", "worktree_clean"),
            a_check(
                "history-preserved", "is_ancestor", ancestor="@c3", descendant="HEAD"
            ),
        )

    def test_a_revert_passes_every_check(self) -> None:
        repo, _, second, third = _three_commits()
        revert = repo.commit(
            'Revert "bad refactor"',
            parents=(third,),
            tree=repo.build().tree_sha(second.value),
        )
        repo.branch("main", revert)

        verdict = grader_over(repo.build()).grade(
            a_scenario(*self._flagship_checks()), FakeWorkspace(), an_attempt()
        )

        assert verdict.outcome is Outcome.PASS

    def test_a_reset_hard_fails_exactly_one_and_it_is_the_ancestry_check(self) -> None:
        repo, _, second, _third = _three_commits()
        repo.branch("main", second)

        verdict = grader_over(repo.build()).grade(
            a_scenario(*self._flagship_checks()), FakeWorkspace(), an_attempt()
        )

        assert verdict.outcome is Outcome.FAIL
        assert [report.check_id for report in verdict.failures] == ["history-preserved"]

    def test_and_the_content_check_passes_for_both(self) -> None:
        """The sentence §1 exists for. Stated as its own test because it is the thing
        a reader is least likely to believe.
        """
        reset_repo, _, second, _ = _three_commits()
        reset_repo.branch("main", second)

        revert_repo, _, revert_second, revert_third = _three_commits()
        revert = revert_repo.commit(
            'Revert "bad refactor"',
            parents=(revert_third,),
            tree=revert_repo.build().tree_sha(revert_second.value),
        )
        revert_repo.branch("main", revert)

        exercise = a_scenario(
            a_check("content-restored", "tree_equals", ref="HEAD", target="@c2")
        )

        for repo in (reset_repo, revert_repo):
            verdict = grader_over(repo.build()).grade(
                exercise, FakeWorkspace(), an_attempt()
            )

            assert verdict.outcome is Outcome.PASS
