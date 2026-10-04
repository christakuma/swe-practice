"""The five assertions over what a drill's answer returned.

Every case runs through the real dispatcher against `FakeDrillQuery`, so what is
being tested is the thing an exercise will actually get.

The cases worth reading are the ones about **what is deliberately not graded**:
row order without `ordered: true`, and the typing of an author's YAML values.
Both are places where a stricter comparison would fail a correct answer, which
is the failure mode a grading engine has to be most careful about — a solver
cannot tell "my SQL is wrong" from "the grader is wrong", so it must not be the
second one.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.fakes.drill import FakeDrillQuery, a_result
from tests.unit.domain.drills.helpers import run


class TestResultMatches:
    def test_passes_when_the_rows_are_the_declared_ones(self) -> None:
        report = run(
            "result_matches",
            FakeDrillQuery(result=a_result()),
            rows=(("alice", 2), ("bob", 0)),
        )

        assert report.passed

    def test_row_order_is_ignored_by_default(self) -> None:
        """The decision `rows.py` argues for: without `ORDER BY`, order is not
        part of the answer, and two solvers who wrote the same query may get
        different orderings.
        """
        report = run(
            "result_matches",
            FakeDrillQuery(result=a_result()),
            rows=(("bob", 0), ("alice", 2)),
        )

        assert report.passed

    def test_row_order_is_graded_when_the_drill_asks_for_it(self) -> None:
        report = run(
            "result_matches",
            FakeDrillQuery(result=a_result()),
            rows=(("bob", 0), ("alice", 2)),
            ordered=True,
        )

        assert not report.passed
        assert "in this order" in (report.expected or "")

    def test_a_duplicate_row_is_a_difference_not_a_set_member(self) -> None:
        """Multiset, not set. A join that doubled every row returns the same
        *distinct* rows and is wrong, which a set comparison would pass.
        """
        doubled = a_result(rows=(("alice", 2), ("alice", 2), ("bob", 0)))

        report = run(
            "result_matches",
            FakeDrillQuery(result=doubled),
            rows=(("alice", 2), ("bob", 0)),
        )

        assert not report.passed

    @pytest.mark.parametrize("declared", [2, "2", 2.0])
    def test_an_authors_value_compares_as_text_whatever_yaml_made_of_it(
        self, declared: object
    ) -> None:
        """`orders: 2` may arrive as an int, a string or a float depending on how
        the YAML was written, and all three mean the same cell.
        """
        report = run(
            "result_matches",
            FakeDrillQuery(result=a_result(rows=(("alice", 2),))),
            rows=(("alice", declared),),
        )

        assert report.passed

    def test_a_null_is_written_as_null_and_compares_to_one(self) -> None:
        report = run(
            "result_matches",
            FakeDrillQuery(result=a_result(rows=(("alice", None),))),
            rows=(("alice", "NULL"),),
        )

        assert report.passed

    def test_a_single_flat_row_is_accepted_as_a_list_of_one(self) -> None:
        """The same kindness `Params.paths` extends: YAML makes both spellings
        look correct and a one-row expectation is the common case.
        """
        report = run(
            "result_matches",
            FakeDrillQuery(result=a_result(rows=(("alice", 2),))),
            rows=("alice", 2),
        )

        assert report.passed

    def test_an_answer_that_did_not_run_reports_sqlites_own_message(self) -> None:
        """The most useful sentence available, and the reason `error` is a string
        on the port rather than an exception off it.
        """
        report = run(
            "result_matches",
            FakeDrillQuery(error='near "FORM": syntax error'),
            rows=(("alice", 2),),
        )

        assert not report.passed
        assert 'near "FORM": syntax error' in (report.actual or "")

    def test_an_answer_that_returned_nothing_says_so_rather_than_erroring(
        self,
    ) -> None:
        report = run("result_matches", FakeDrillQuery(), rows=(("alice", 2),))

        assert not report.passed
        assert "returned no rows" in (report.actual or "")

    def test_ragged_declared_rows_are_an_authoring_error(self) -> None:
        """Rows of different widths can never all match, so at least one check is
        dead on arrival -- which is reported as a misconfiguration, not a failure
        a solver could act on.
        """
        report = run(
            "result_matches",
            FakeDrillQuery(result=a_result()),
            rows=(("alice", 2), ("bob",)),
        )

        assert not report.passed
        assert "misconfigured" in (report.actual or "")
        assert "same number of values" in (report.actual or "")

    def test_a_missing_rows_parameter_is_an_authoring_error(self) -> None:
        report = run("result_matches", FakeDrillQuery(result=a_result()))

        assert not report.passed
        assert "missing required parameter 'rows'" in (report.actual or "")

    def test_a_nested_list_where_a_value_belongs_is_an_authoring_error(self) -> None:
        report = run(
            "result_matches",
            FakeDrillQuery(result=a_result()),
            rows=((("alice", 2),),),
        )

        assert not report.passed
        assert "nested list" in (report.actual or "")

    def test_a_verdict_states_the_count_even_when_it_truncates(self) -> None:
        """A wrong answer can return the whole table; a panel that pasted two
        hundred rows into it is a panel nobody reads.
        """
        many = a_result(rows=tuple((f"c{n}", n) for n in range(40)))

        report = run(
            "result_matches", FakeDrillQuery(result=many), rows=(("alice", 2),)
        )

        assert "40 rows" in (report.actual or "")
        assert (report.actual or "").endswith("| ...")


class TestResultRowCount:
    @pytest.mark.parametrize(
        ("params", "passed"),
        [
            ({"equals": 2}, True),
            ({"equals": 3}, False),
            ({"at_least": 2}, True),
            ({"at_least": 3}, False),
            ({"at_most": 2}, True),
            ({"at_most": 1}, False),
        ],
    )
    def test_it_compares_the_way_the_author_asked(
        self, params: dict[str, Any], passed: bool
    ) -> None:
        report = run("result_row_count", FakeDrillQuery(result=a_result()), **params)

        assert report.passed is passed

    def test_zero_rows_is_a_real_answer_an_author_can_assert(self) -> None:
        """Distinct from an answer that returned nothing at all -- which is the
        distinction `NO_RESULT` exists for.
        """
        empty = a_result(rows=())

        assert run("result_row_count", FakeDrillQuery(result=empty), equals=0).passed
        assert not run("result_row_count", FakeDrillQuery(), equals=0).passed

    def test_needing_exactly_one_comparison_is_enforced(self) -> None:
        report = run("result_row_count", FakeDrillQuery(result=a_result()))

        assert not report.passed
        assert "exactly one of" in (report.actual or "")

    def test_an_answer_that_did_not_run_fails_rather_than_counting_zero(self) -> None:
        report = run(
            "result_row_count", FakeDrillQuery(error="no such table: ordrs"), equals=0
        )

        assert not report.passed
        assert "no such table: ordrs" in (report.actual or "")


class TestResultContainsRow:
    def test_passes_when_the_row_is_in_there_somewhere(self) -> None:
        report = run(
            "result_contains_row", FakeDrillQuery(result=a_result()), row=("bob", 0)
        )

        assert report.passed

    def test_the_outer_join_case_it_was_written_for(self) -> None:
        """The customer with no orders still gets a row, with zero -- one row out
        of eight, asserted on its own so the verdict names what is missing.
        """
        inner_join_only = a_result(rows=(("alice", 2), ("carol", 1)))

        report = run(
            "result_contains_row",
            FakeDrillQuery(result=inner_join_only),
            row=("bob", 0),
        )

        assert not report.passed
        assert "a row bob, 0" in (report.expected or "")

    def test_negated_is_how_a_drill_says_this_row_must_not_be_here(self) -> None:
        report = run(
            "result_contains_row",
            FakeDrillQuery(result=a_result()),
            row=("bob", 0),
            negated=True,
        )

        assert not report.passed
        assert (report.expected or "").startswith("not ")

    def test_two_rows_under_row_is_an_authoring_error(self) -> None:
        """One check per row. Grading the first silently would be a check that
        tests less than it says.
        """
        report = run(
            "result_contains_row",
            FakeDrillQuery(result=a_result()),
            row=(("alice", 2), ("bob", 0)),
        )

        assert not report.passed
        assert "takes one row, got 2" in (report.actual or "")


class TestResultColumns:
    def test_passes_on_the_declared_columns_in_the_declared_order(self) -> None:
        report = run(
            "result_columns",
            FakeDrillQuery(result=a_result()),
            columns=("name", "orders"),
        )

        assert report.passed

    def test_column_order_is_graded_by_default(self) -> None:
        """The asymmetry with `result_matches`, and it is real: a column list is
        written by hand in the SELECT clause, so its order is always the author's
        choice and always reproducible.
        """
        report = run(
            "result_columns",
            FakeDrillQuery(result=a_result()),
            columns=("orders", "name"),
        )

        assert not report.passed

    def test_order_can_be_waived(self) -> None:
        report = run(
            "result_columns",
            FakeDrillQuery(result=a_result()),
            columns=("orders", "name"),
            ordered=False,
        )

        assert report.passed

    def test_it_is_what_makes_select_star_gradeable(self) -> None:
        everything = a_result(columns=("id", "name", "email", "orders"))

        report = run(
            "result_columns",
            FakeDrillQuery(result=everything),
            columns=("name", "orders"),
        )

        assert not report.passed
        assert "id, name, email, orders" in (report.actual or "")

    def test_a_single_column_name_is_accepted_as_a_list_of_one(self) -> None:
        report = run(
            "result_columns",
            FakeDrillQuery(result=a_result(columns=("name",), rows=(("alice",),))),
            columns="name",
        )

        assert report.passed

    def test_an_answer_that_did_not_run_has_no_columns_to_compare(self) -> None:
        report = run(
            "result_columns", FakeDrillQuery(error="syntax error"), columns="name"
        )

        assert not report.passed
        assert "syntax error" in (report.actual or "")


class TestResultOrderedBy:
    def test_passes_when_the_named_column_is_ascending(self) -> None:
        report = run(
            "result_ordered_by",
            FakeDrillQuery(result=a_result(rows=(("alice", 2), ("bob", 0)))),
            column="name",
        )

        assert report.passed

    def test_passes_when_the_named_column_is_descending_and_asked_to_be(self) -> None:
        report = run(
            "result_ordered_by",
            FakeDrillQuery(result=a_result(rows=(("bob", 0), ("alice", 2)))),
            column="name",
            descending=True,
        )

        assert report.passed

    def test_fails_on_the_wrong_direction_and_names_the_property(self) -> None:
        """What `result_matches {ordered: true}` cannot say: the verdict names
        *sorted by name descending* rather than making a solver diff rows.
        """
        report = run(
            "result_ordered_by",
            FakeDrillQuery(result=a_result(rows=(("alice", 2), ("bob", 0)))),
            column="name",
            descending=True,
        )

        assert not report.passed
        assert report.expected == "rows sorted by name, descending"

    def test_a_column_the_answer_did_not_select_is_a_clean_failure(self) -> None:
        report = run(
            "result_ordered_by", FakeDrillQuery(result=a_result()), column="total"
        )

        assert not report.passed
        assert "no column total in name, orders" in (report.actual or "")

    def test_an_empty_result_is_trivially_sorted(self) -> None:
        """Vacuous, and correctly so: a drill that cares whether rows came back
        asserts `result_row_count` beside this, which is why both exist.
        """
        report = run(
            "result_ordered_by",
            FakeDrillQuery(result=a_result(columns=("name",), rows=())),
            column="name",
        )

        assert report.passed

    def test_an_answer_that_did_not_run_fails(self) -> None:
        report = run(
            "result_ordered_by", FakeDrillQuery(error="syntax error"), column="name"
        )

        assert not report.passed
