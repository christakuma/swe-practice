"""The two assertions over how the answer got there.

Both advisory by convention, and both most useful negated — which is why most of
these cases pass `negated=True`. `not sql_matches /select\\s+\\*/` is how a drill
says *name your columns*; `not query_plan_matches /\\bSCAN\\b/` is how it says
*that index exists, use it*. Neither fails a correct answer; both turn a `PASS`
into a `PASS_WITH_ADVISORIES`, which is §4.4's mechanism carrying the most
transferable thing in the SQL track.
"""

from __future__ import annotations

from tests.fakes.drill import FakeDrillQuery
from tests.unit.domain.drills.helpers import run

SLOW_PLAN = ("SCAN orders", "USE TEMP B-TREE FOR ORDER BY")
FAST_PLAN = ("SEARCH orders USING INDEX idx_orders_customer (customer=?)",)


class TestSqlMatches:
    def test_passes_when_a_statement_matches(self) -> None:
        report = run(
            "sql_matches",
            FakeDrillQuery(statements=("SELECT name FROM customers LEFT JOIN o",)),
            pattern=r"left\s+join",
        )

        assert report.passed

    def test_matching_ignores_case_because_both_spellings_are_reasonable(
        self,
    ) -> None:
        """An author who wrote `JOIN` did not mean to fail `join`."""
        report = run(
            "sql_matches",
            FakeDrillQuery(statements=("select name from customers left join o",)),
            pattern=r"LEFT JOIN",
        )

        assert report.passed

    def test_it_searches_every_statement_not_only_the_last(self) -> None:
        report = run(
            "sql_matches",
            FakeDrillQuery(
                statements=("CREATE TEMP VIEW v AS SELECT 1", "SELECT * FROM v")
            ),
            pattern=r"create\s+temp\s+view",
        )

        assert report.passed

    def test_it_reports_which_statement_matched(self) -> None:
        """The negated form is the common one, and "nothing matched" is useless
        feedback next to the line that did.
        """
        report = run(
            "sql_matches",
            FakeDrillQuery(statements=("SELECT * FROM orders",)),
            pattern=r"select\s+\*",
            negated=True,
        )

        assert not report.passed
        assert "'SELECT * FROM orders'" in (report.actual or "")

    def test_naming_your_columns_passes_the_negated_form(self) -> None:
        report = run(
            "sql_matches",
            FakeDrillQuery(statements=("SELECT name, total FROM orders",)),
            pattern=r"select\s+\*",
            negated=True,
        )

        assert report.passed

    def test_a_quoted_statement_is_flattened_and_capped(self) -> None:
        """A statement can be the whole answer; a panel that pasted forty lines
        of SQL into the `actual` field would bury what it is reporting.
        """
        # Suppressed below: this SQL is the subject under test, not a query
        # anything runs.
        sprawling = "SELECT *\n  FROM orders\n  WHERE " + " OR ".join(  # noqa: S608
            f"id = {n}" for n in range(40)
        )

        report = run(
            "sql_matches",
            FakeDrillQuery(statements=(sprawling,)),
            pattern=r"select\s+\*",
        )

        assert "\n" not in (report.actual or "")
        assert (report.actual or "").endswith("...'")

    def test_no_sql_at_all_says_so(self) -> None:
        report = run("sql_matches", FakeDrillQuery(), pattern=r"join")

        assert not report.passed
        assert report.actual == "<no SQL was submitted>"

    def test_a_pattern_that_will_not_compile_is_an_authoring_error(self) -> None:
        report = run(
            "sql_matches", FakeDrillQuery(statements=("SELECT 1",)), pattern="("
        )

        assert not report.passed
        assert "misconfigured" in (report.actual or "")
        assert "not a valid regular expression" in (report.actual or "")


class TestQueryPlanMatches:
    def test_passes_when_a_plan_line_matches(self) -> None:
        report = run(
            "query_plan_matches",
            FakeDrillQuery(plan=FAST_PLAN),
            pattern=r"USING INDEX",
        )

        assert report.passed

    def test_the_advisory_this_kind_exists_for(self) -> None:
        """Two answers returning identical rows can differ by a factor of a
        thousand in work done, and SQLite says which is which.
        """
        slow = run(
            "query_plan_matches",
            FakeDrillQuery(plan=SLOW_PLAN),
            pattern=r"\bSCAN\b",
            negated=True,
        )
        fast = run(
            "query_plan_matches",
            FakeDrillQuery(plan=FAST_PLAN),
            pattern=r"\bSCAN\b",
            negated=True,
        )

        assert not slow.passed
        assert fast.passed

    def test_matching_is_case_sensitive_unlike_sql_matches(self) -> None:
        """The plan is SQLite's output rather than the solver's input, and a
        case-insensitive `\\bscan\\b` would also match a table called `scans`.
        """
        report = run(
            "query_plan_matches",
            FakeDrillQuery(plan=("SCAN orders",)),
            pattern=r"\bscan\b",
        )

        assert not report.passed

    def test_a_failure_shows_the_plan_it_did_see(self) -> None:
        report = run(
            "query_plan_matches",
            FakeDrillQuery(plan=SLOW_PLAN),
            pattern=r"USING INDEX",
        )

        assert not report.passed
        assert "'SCAN orders'" in (report.actual or "")
        assert "'USE TEMP B-TREE FOR ORDER BY'" in (report.actual or "")

    def test_no_plan_at_all_says_so(self) -> None:
        """Which is the state an answer that did not run leaves behind, and an
        answer that returned no rows."""
        report = run("query_plan_matches", FakeDrillQuery(), pattern=r"\bSCAN\b")

        assert not report.passed
        assert report.actual == "<there was no query plan>"
