"""The two assertions that read the attempt's command log, not the repository.

Both are built from real `Attempt` aggregates — `an_attempt` drives
`record_command` rather than poking at the event list — so a command the exercise
would not allow cannot get into a test's log. A test that bypassed that would be
asserting about a log the product cannot produce.

The patterns used here are the ones that actually ship in `content/`, copied rather
than invented. An assertion whose unit tests use friendlier patterns than the
exercises do is an assertion that has not been tested.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from practice.domain.verdict import Severity
from tests.fakes import a_repo
from tests.unit.domain.checks.helpers import an_attempt, run

if TYPE_CHECKING:
    from tests.fakes import FakeRepoQuery

#: `looked-before-leaping`, from `git/revert-a-pushed-commit`.
INSPECTED: Final = r"^git (log|show|status|diff|reflog)\b"

#: `no-force-push`, from the same exercise. Carried with `not: true`.
FORCE_PUSH: Final = r"push\b.*(--force|--force-with-lease|-f)\b"

#: `used-the-reflog`, from `git/recover-a-lost-commit`.
REFLOG: Final = r"^git (reflog\b|log\b.*(-g\b|--walk-reflogs\b))"


def _query() -> FakeRepoQuery:
    """These assertions never touch the repository; one is still required.

    Passing an empty one is the honest way to say so — and if an implementation ever
    started reading the repository, these tests would be the ones that noticed.
    """
    return a_repo().build()


class TestCommandUsed:
    def test_it_finds_a_matching_command_and_quotes_it(self) -> None:
        attempt = an_attempt(
            [
                ["git", "status", "--short", "--branch"],
                ["git", "revert", "--no-edit", "HEAD"],
            ]
        )

        report = run(_query(), "command_used", attempt=attempt, pattern=INSPECTED)

        assert report.passed is True
        assert "git status --short --branch" in (report.actual or "")

    def test_it_fails_when_nothing_matches_and_says_how_many_it_read(self) -> None:
        attempt = an_attempt(
            [["git", "revert", "--no-edit", "HEAD"], ["git", "push", "origin", "main"]]
        )

        report = run(_query(), "command_used", attempt=attempt, pattern=INSPECTED)

        assert report.passed is False
        assert report.actual == "no match in 2 commands"

    def test_an_attempt_that_ran_nothing_says_so(self) -> None:
        """ "No match in 0 commands" and "no match in 14 commands" are different
        situations, and the first is a solver who submitted without doing anything.
        """
        report = run(_query(), "command_used", attempt=an_attempt(), pattern=INSPECTED)

        assert report.passed is False
        assert report.actual == "no match in 0 commands"

    def test_negated_it_flags_a_force_push(self) -> None:
        """`no-force-push`, failing: a correct revert fast-forwards, so reaching for
        `--force` on a shared branch is the habit the exercise exists to break — and
        the attempt still produced the right tree, which is why it is advisory.
        """
        attempt = an_attempt(
            [
                ["git", "reset", "--hard", "HEAD~1"],
                ["git", "push", "--force", "origin", "main"],
            ]
        )

        report = run(
            _query(),
            "command_used",
            attempt=attempt,
            pattern=FORCE_PUSH,
            negated=True,
            severity=Severity.ADVISORY,
        )

        assert report.passed is False
        assert report.is_blocking is False
        assert report.expected == f"not a command matching /{FORCE_PUSH}/"

    def test_negated_it_passes_on_a_plain_push(self) -> None:
        attempt = an_attempt(
            [["git", "revert", "--no-edit", "HEAD"], ["git", "push", "origin", "main"]]
        )

        assert (
            run(
                _query(),
                "command_used",
                attempt=attempt,
                pattern=FORCE_PUSH,
                negated=True,
            ).passed
            is True
        )

    @pytest.mark.parametrize(
        "argv",
        [
            ["git", "push", "--force", "origin", "main"],
            ["git", "push", "--force-with-lease", "origin", "main"],
            ["git", "push", "-f", "origin", "main"],
        ],
    )
    def test_the_shipped_force_push_pattern_catches_every_spelling(
        self, argv: list[str]
    ) -> None:
        """Including `--force-with-lease`, which is the *safer* one and still a
        rewrite of a branch other people have pulled.
        """
        attempt = an_attempt([argv])

        assert (
            run(_query(), "command_used", attempt=attempt, pattern=FORCE_PUSH).passed
            is True
        )

    def test_it_matches_the_normalised_line_not_what_was_typed(self) -> None:
        """`CommandRun.command_line` is `shlex.join` of the argv, so a pattern sees
        one space between arguments whatever the solver typed. Without that, every
        author's pattern would need `\\s+` where a space belongs.
        """
        attempt = an_attempt([["git", "log", "--oneline", "--decorate", "--all"]])

        assert (
            run(
                _query(),
                "command_used",
                attempt=attempt,
                pattern=r"^git log --oneline --decorate --all$",
            ).passed
            is True
        )

    def test_the_reflog_pattern_matches_both_ways_of_reading_one(self) -> None:
        """`git reflog` and `git log -g` are the same operation, and an exercise that
        rewarded only the first would be grading vocabulary rather than skill.
        """
        for argv in (["git", "reflog"], ["git", "log", "-g", "--oneline"]):
            assert (
                run(
                    _query(), "command_used", attempt=an_attempt([argv]), pattern=REFLOG
                ).passed
                is True
            )

    def test_it_needs_a_pattern(self) -> None:
        report = run(_query(), "command_used", attempt=an_attempt())

        assert report.passed is False
        assert "misconfigured" in (report.actual or "")


class TestCommandCount:
    def test_it_passes_inside_the_budget(self) -> None:
        attempt = an_attempt([["git", "status"], ["git", "revert", "HEAD"]])

        report = run(_query(), "command_count", attempt=attempt, at_most=5)

        assert report.passed is True
        assert report.actual == "2 commands"

    def test_it_fails_over_the_budget(self) -> None:
        attempt = an_attempt([["git", "status"]] * 4)

        report = run(_query(), "command_count", attempt=attempt, at_most=3)

        assert report.passed is False
        assert report.expected == "at most 3 commands"

    def test_one_command_reads_as_one_command(self) -> None:
        attempt = an_attempt([["git", "status"]])

        assert (
            run(_query(), "command_count", attempt=attempt, at_most=1).actual
            == "1 command"
        )

    def test_it_takes_at_most_and_nothing_else(self) -> None:
        """`equals` would grade a solver for typing a specific number of commands and
        `at_least` would reward thrashing, so the shared `comparison()` helper is
        deliberately not used here.
        """
        attempt = an_attempt([["git", "status"]])

        report = run(_query(), "command_count", attempt=attempt, equals=1)

        assert report.passed is False
        assert "at_most" in (report.actual or "")

    def test_it_counts_read_only_commands_which_is_why_it_is_on_probation(self) -> None:
        """The probation, as a test rather than a comment.

        Every command in this attempt is read-only -- it is the recovery scenario's
        reference solution, which is mostly inspection -- and a `command_count
        {at_most: 5}` budget fails it. The same attempt passes `used-the-reflog`,
        which *rewards* that inspection. The two checks pull in opposite directions
        on one correct answer, and that is the argument for deleting this assertion
        rather than tuning the number.

        Making it useful needs a `mutating_only: true` filter, which needs a
        maintained list of read-only git subcommands -- a list that is wrong the
        first time git adds one.
        """
        inspection = an_attempt(
            [
                ["git", "status", "--short", "--branch"],
                ["git", "log", "--oneline", "--decorate", "--all"],
                ["ls"],
                ["git", "reflog"],
                ["git", "show", "--stat", "HEAD@{3}"],
                ["git", "reset", "--hard", "HEAD@{3}"],
            ]
        )

        budget = run(_query(), "command_count", attempt=inspection, at_most=5)
        reflog = run(_query(), "command_used", attempt=inspection, pattern=REFLOG)

        assert budget.passed is False
        assert reflog.passed is True
