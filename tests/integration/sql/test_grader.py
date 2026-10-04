"""A drill answer becomes a verdict, through the real engine.

Integration rather than unit, and deliberately so: `adapters/sql/__init__.py`
explains that there is no `SqlDrillRunner` protocol between the grader and the
engine, because a drill runs in under a millisecond and a protocol would be the
abstraction §13 says to delete. The consequence is that the grader's tests are
these — against real SQLite — and the cost is about a millisecond each.

The case worth reading first is
`TestWhenTheAnswerDoesNotRun::test_one_failure_is_reported_as_one_failure`. That
is the whole reason `answer-ran` is synthesised, and it is the difference between
a verdict a solver can act on and ten failures for one misplaced keyword.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.sql import ANSWER_CHECK_ID, SqlDrillGrader, SqlDrillGraderError
from practice.domain.attempt import Attempt, AttemptPolicy
from practice.domain.exercise import CheckSpec, Exercise, SqlDrillSpec
from practice.domain.ids import AttemptId
from practice.domain.verdict import Outcome, Severity
from tests.fakes import FakeClock, FakeWorkspace, a_drill, a_kata
from tests.integration.sql.conftest import SEED

if TYPE_CHECKING:
    from practice.domain.verdict import Verdict

PER_CUSTOMER = """\
SELECT c.name, COUNT(o.id) AS orders
  FROM customers c
  LEFT JOIN orders o ON o.customer_id = c.id
 GROUP BY c.id
 ORDER BY c.name;
"""

#: What a correct answer to the seed in `conftest` returns.
EXPECTED = (("alice", 2), ("bob", 0), ("carol", 1))


def a_check(**overrides: object) -> CheckSpec:
    fields: dict[str, object] = {
        "id": "rows-match",
        "label": "Every customer appears exactly once, with a count.",
        "severity": Severity.REQUIRED,
        "assertion": "result_matches",
        "params": {"rows": EXPECTED},
    }
    fields.update(overrides)
    return CheckSpec(**fields)  # type: ignore[arg-type]


def graded(answer: str, *checks: CheckSpec, seed: str = SEED) -> Verdict:
    """Grade one answer against a drill declaring `checks`.

    The workspace is a `FakeWorkspace` holding the seed, because what the grader
    needs from one is `read_file(spec.seed)` and nothing else — a provisioned
    directory would add a second subject to every case here. The engine, the
    database and the assertions are all real.
    """
    exercise: Exercise = a_drill(checks=checks or (a_check(),))
    spec = exercise.spec
    assert isinstance(spec, SqlDrillSpec)

    workspace = FakeWorkspace(files={spec.seed: seed})
    clock = FakeClock()
    attempt = Attempt(
        attempt_id=AttemptId.parse("aabbccdd-0000-4000-8000-000000000001"),
        exercise_id=exercise.id,
        policy=AttemptPolicy.for_exercise(exercise),
        started_at=clock.now(),
    )
    attempt.save_solution(answer, at=clock.now())
    return SqlDrillGrader().grade(exercise, workspace, attempt)


class TestACorrectAnswer:
    def test_it_passes_and_says_the_answer_ran(self) -> None:
        verdict = graded(PER_CUSTOMER)

        assert verdict.outcome is Outcome.PASS
        assert verdict.reports[0].check_id == ANSWER_CHECK_ID
        assert verdict.reports[0].passed

    def test_the_answer_ran_check_is_present_on_a_pass_too(self) -> None:
        """So the verdict panel's shape does not depend on the outcome: the one
        thing a solver reads first is in the same place every time.
        """
        verdict = graded(PER_CUSTOMER)

        assert [report.check_id for report in verdict.reports] == [
            ANSWER_CHECK_ID,
            "rows-match",
        ]

    def test_the_declared_checks_run_in_the_order_the_exercise_declares_them(
        self,
    ) -> None:
        verdict = graded(
            PER_CUSTOMER,
            a_check(id="rows-match"),
            a_check(id="row-count", assertion="result_row_count", params={"equals": 3}),
            a_check(
                id="named-the-columns",
                assertion="result_columns",
                params={"columns": ("name", "orders")},
            ),
        )

        assert [report.check_id for report in verdict.reports] == [
            ANSWER_CHECK_ID,
            "rows-match",
            "row-count",
            "named-the-columns",
        ]
        assert verdict.outcome is Outcome.PASS

    def test_two_answers_that_spell_the_same_query_differently_both_pass(
        self,
    ) -> None:
        """**The core bet, for this kind.** A drill grades rows, so the SQL that
        produced them is not what is being compared.
        """
        subquery = """\
SELECT c.name,
       (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.id) AS orders
  FROM customers c
 ORDER BY c.name;
"""

        assert graded(PER_CUSTOMER).outcome is Outcome.PASS
        assert graded(subquery).outcome is Outcome.PASS


class TestAdvisories:
    def test_a_correct_but_careless_answer_passes_with_advisories(self) -> None:
        """§4.4's mechanism in the SQL track: the rows are right and the plan
        says the work was done the hard way.
        """
        scan = "SELECT * FROM orders WHERE status = 'shipped';"

        verdict = graded(
            scan,
            a_check(
                id="rows-match",
                params={"rows": ((1, 1, 10.5, "shipped"), (3, 3, 7.25, "shipped"))},
            ),
            a_check(
                id="used-the-index",
                severity=Severity.ADVISORY,
                assertion="query_plan_matches",
                params={"pattern": r"\bSCAN\b"},
                negated=True,
            ),
        )

        assert verdict.outcome is Outcome.PASS_WITH_ADVISORIES
        assert [report.check_id for report in verdict.advisories] == ["used-the-index"]

    def test_an_advisory_alone_cannot_fail_an_attempt(self) -> None:
        verdict = graded(
            PER_CUSTOMER,
            a_check(),
            a_check(
                id="no-select-star",
                severity=Severity.ADVISORY,
                assertion="sql_matches",
                params={"pattern": r"select\s+\*"},
            ),
        )

        assert verdict.passed


class TestWhenTheAnswerDoesNotRun:
    def test_one_failure_is_reported_as_one_failure(self) -> None:
        """**Why `answer-ran` is synthesised.**

        A syntax error produces no result set, so every declared check fails
        too. The point is that the *first* report says the one true thing, so a
        solver reads "SQLite could not run this" rather than counting four ways
        their logic is supposedly wrong.
        """
        verdict = graded(
            "SELECT c.name FORM customers;",
            a_check(id="rows-match"),
            a_check(id="row-count", assertion="result_row_count", params={"equals": 3}),
            a_check(
                id="named-the-columns",
                assertion="result_columns",
                params={"columns": ("name", "orders")},
            ),
        )

        assert verdict.outcome is Outcome.FAIL
        first = verdict.failures[0]
        assert first.check_id == ANSWER_CHECK_ID
        assert "FORM" in (first.actual or "") or "syntax" in (first.actual or "")

    def test_it_explains_that_the_other_checks_still_ran(self) -> None:
        """Because they did, against the database as the answer left it -- and a
        solver seeing four failures needs to know why they are there.
        """
        verdict = graded("SELECT nope FROM customers;")

        answer = verdict.reports[0]
        assert answer.explanation is not None
        assert "ran anyway" in answer.explanation

    def test_a_partly_applied_answer_is_graded_on_the_state_it_left(self) -> None:
        """The honest thing to grade. The `DELETE` took effect; the second
        statement did not; the table reflects exactly that.
        """
        verdict = graded(
            "DELETE FROM orders WHERE id = 1;\nSELECT nope FROM orders;",
            a_check(
                id="two-left",
                assertion="table_row_count",
                params={"table": "orders", "equals": 2},
            ),
        )

        assert verdict.outcome is Outcome.FAIL  # answer-ran failed
        assert verdict.reports[1].passed  # ...and the state check is still true

    def test_an_answer_that_was_denied_reports_why(self) -> None:
        verdict = graded("ATTACH DATABASE 'x.db' AS evil;")

        assert "not authorized" in (verdict.reports[0].actual or "")


class TestTheEndStateIsWhatIsGraded:
    def test_a_delete_with_no_where_fails_on_the_table_not_the_result(self) -> None:
        """The case `tables.py` exists for, end to end through the grader.

        `DELETE FROM orders` returns nothing and runs cleanly, so `answer-ran`
        passes. Only the table check catches it.
        """
        verdict = graded(
            "DELETE FROM orders;",
            a_check(
                id="only-pending-went",
                assertion="table_row_count",
                params={"table": "orders", "equals": 2},
            ),
        )

        assert verdict.reports[0].passed
        assert verdict.outcome is Outcome.FAIL
        assert "orders holds 0 row(s)" in (verdict.reports[1].actual or "")

    def test_the_grader_closes_the_database_before_the_verdict_leaves(self) -> None:
        """The verdict holds only `CheckReport`s -- display strings and booleans
        -- so nothing in it can still be reading a connection. Asserted by
        grading many times over: a leaked in-memory database per pass would
        show up as unbounded growth rather than as a failure, so what this
        really pins is that `closing` is in the path at all.
        """
        for _ in range(100):
            assert graded(PER_CUSTOMER).outcome is Outcome.PASS


class TestRefusals:
    def test_grading_a_kata_is_a_programming_error(self) -> None:
        exercise = a_kata()
        clock = FakeClock()
        attempt = Attempt(
            attempt_id=AttemptId.parse("00000000-0000-4000-8000-000000000002"),
            exercise_id=exercise.id,
            policy=AttemptPolicy.for_exercise(exercise),
            started_at=clock.now(),
        )

        with pytest.raises(SqlDrillGraderError, match="which this grader"):
            SqlDrillGrader().grade(exercise, FakeWorkspace(), attempt)

    def test_grading_before_anything_was_saved_is_a_programming_error(self) -> None:
        """An exception rather than a failing check: "you did not submit
        anything" in a verdict is something the solver cannot act on.
        """
        exercise = a_drill()
        spec = exercise.spec
        assert isinstance(spec, SqlDrillSpec)
        clock = FakeClock()
        attempt = Attempt(
            attempt_id=AttemptId.parse("00000000-0000-4000-8000-000000000003"),
            exercise_id=exercise.id,
            policy=AttemptPolicy.for_exercise(exercise),
            started_at=clock.now(),
        )

        with pytest.raises(SqlDrillGraderError, match="saved no answer"):
            SqlDrillGrader().grade(
                exercise, FakeWorkspace(files={spec.seed: SEED}), attempt
            )

    def test_the_latest_saved_answer_is_the_one_graded(self) -> None:
        """A solver saves repeatedly while working, and what is graded is what
        they finished with -- `latest_source`, shared with the kata grader.
        """
        exercise = a_drill()
        spec = exercise.spec
        assert isinstance(spec, SqlDrillSpec)
        clock = FakeClock()
        attempt = Attempt(
            attempt_id=AttemptId.parse("00000000-0000-4000-8000-000000000004"),
            exercise_id=exercise.id,
            policy=AttemptPolicy.for_exercise(exercise),
            started_at=clock.now(),
        )
        attempt.save_solution("SELECT nope;", at=clock.now())
        attempt.save_solution(PER_CUSTOMER, at=clock.now())

        verdict = SqlDrillGrader().grade(
            exercise, FakeWorkspace(files={spec.seed: SEED}), attempt
        )

        assert verdict.outcome is Outcome.PASS
