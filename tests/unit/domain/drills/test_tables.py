"""The three assertions over what the database was left holding.

This is the file that holds the core bet for this exercise kind, and the case
worth reading first is `test_a_delete_with_no_where_is_caught_by_the_table_and
_not_by_the_result`: an answer that emptied a table returns nothing, so every
assertion in `test_rows.py` is blind to it. §6.6 made the same point about git —
`content-restored` passes for a revert, a `reset --hard` and a forgotten push
alike — and the answer is the same shape of answer. The discriminating check is
about the state afterwards.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.fakes.drill import FakeDrillQuery, a_result
from tests.unit.domain.drills.helpers import run

ORDERS = a_result(
    columns=("id", "customer", "status"),
    rows=((1, "alice", "shipped"), (2, "bob", "pending")),
)


class TestTableMatches:
    def test_passes_when_the_table_holds_the_declared_rows(self) -> None:
        report = run(
            "table_matches",
            FakeDrillQuery(tables={"orders": ORDERS}),
            table="orders",
            rows=((1, "alice", "shipped"), (2, "bob", "pending")),
        )

        assert report.passed

    def test_row_order_is_ignored_by_default(self) -> None:
        report = run(
            "table_matches",
            FakeDrillQuery(tables={"orders": ORDERS}),
            table="orders",
            rows=((2, "bob", "pending"), (1, "alice", "shipped")),
        )

        assert report.passed

    def test_insertion_order_can_be_graded(self) -> None:
        """Meaningful because the port returns rows in `rowid` order, which is
        what an INSERT drill wants to assert and an UPDATE drill wants to ignore.
        """
        report = run(
            "table_matches",
            FakeDrillQuery(tables={"orders": ORDERS}),
            table="orders",
            rows=((2, "bob", "pending"), (1, "alice", "shipped")),
            ordered=True,
        )

        assert not report.passed

    def test_an_update_that_touched_too_much_is_caught(self) -> None:
        """The failure `table_matches` exists for. Grading only the rows the drill
        expected to change would pass an answer that changed those *and* others,
        which is why this compares the whole table.
        """
        over_reached = a_result(
            columns=("id", "customer", "status"),
            rows=((1, "alice", "shipped"), (2, "bob", "shipped")),
        )

        report = run(
            "table_matches",
            FakeDrillQuery(tables={"orders": over_reached}),
            table="orders",
            rows=((1, "alice", "shipped"), (2, "bob", "pending")),
        )

        assert not report.passed
        assert "orders holds" in (report.actual or "")

    def test_a_delete_with_no_where_is_caught_by_the_table_and_not_by_the_result(
        self,
    ) -> None:
        """The core-bet case for this kind, stated as a test.

        An answer that emptied the table returned no rows, so nothing in
        `test_rows.py` can see it -- `result_row_count {equals: 0}` would even
        *pass*. What tells the right answer from the catastrophic one is the
        table.
        """
        emptied = a_result(columns=("id", "customer", "status"), rows=())
        db = FakeDrillQuery(tables={"orders": emptied})

        assert run("result_row_count", db, equals=0).passed is False  # no result
        assert not run(
            "table_matches",
            db,
            table="orders",
            rows=((1, "alice", "shipped"),),
        ).passed

    def test_a_table_the_answer_dropped_is_a_clean_failure(self) -> None:
        report = run(
            "table_matches",
            FakeDrillQuery(tables={}),
            table="orders",
            rows=((1, "alice", "shipped"),),
        )

        assert not report.passed
        assert report.actual == "<no such table>"

    def test_the_expected_string_names_the_table(self) -> None:
        """So a drill with three table checks produces three readable lines
        rather than three identical ones.
        """
        report = run(
            "table_matches",
            FakeDrillQuery(tables={"orders": ORDERS}),
            table="orders",
            rows=((9, "nobody", "void"),),
        )

        assert (report.expected or "").startswith("orders holding 1 rows")


class TestTableRowCount:
    @pytest.mark.parametrize(
        ("params", "passed"),
        [
            ({"equals": 2}, True),
            ({"equals": 0}, False),
            ({"at_least": 1}, True),
            ({"at_most": 1}, False),
        ],
    )
    def test_it_compares_the_way_the_author_asked(
        self, params: dict[str, Any], passed: bool
    ) -> None:
        report = run(
            "table_row_count",
            FakeDrillQuery(tables={"orders": ORDERS}),
            table="orders",
            **params,
        )

        assert report.passed is passed

    def test_it_separates_a_delete_that_matched_nothing_from_one_that_emptied(
        self,
    ) -> None:
        """Both return no rows; the single number is what tells them apart, and
        it is the one thing a solver can act on.
        """
        emptied = FakeDrillQuery(tables={"orders": a_result(columns=("id",), rows=())})
        untouched = FakeDrillQuery(tables={"orders": ORDERS})

        assert run("table_row_count", emptied, table="orders", equals=1).passed is False
        assert (
            run("table_row_count", untouched, table="orders", equals=1).passed is False
        )
        assert "orders holds 0 row(s)" in (
            run("table_row_count", emptied, table="orders", equals=1).actual or ""
        )

    def test_a_missing_table_fails_rather_than_counting_zero(self) -> None:
        report = run(
            "table_row_count", FakeDrillQuery(tables={}), table="orders", equals=0
        )

        assert not report.passed
        assert report.actual == "<no such table>"

    def test_a_missing_table_parameter_is_an_authoring_error(self) -> None:
        report = run(
            "table_row_count", FakeDrillQuery(tables={"orders": ORDERS}), equals=2
        )

        assert not report.passed
        assert "missing required parameter 'table'" in (report.actual or "")


class TestTableExists:
    def test_passes_when_the_name_is_there(self) -> None:
        report = run(
            "table_exists",
            FakeDrillQuery(tables={"order_totals": ORDERS}),
            table="order_totals",
        )

        assert report.passed

    def test_the_actual_lists_what_is_there_because_the_failure_is_a_typo(
        self,
    ) -> None:
        report = run(
            "table_exists",
            FakeDrillQuery(tables={"orders": ORDERS, "customers": ORDERS}),
            table="order",
        )

        assert not report.passed
        assert report.actual == "customers, orders"

    def test_an_empty_database_says_so_rather_than_listing_nothing(self) -> None:
        report = run("table_exists", FakeDrillQuery(tables={}), table="orders")

        assert not report.passed
        assert report.actual == "<no tables at all>"

    def test_negated_is_how_a_drill_grades_a_drop(self) -> None:
        report = run(
            "table_exists",
            FakeDrillQuery(tables={"customers": ORDERS}),
            table="orders_backup",
            negated=True,
        )

        assert report.passed
        assert (report.expected or "").startswith("not a table or view")
