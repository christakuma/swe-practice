"""The drill engine against a real SQLite connection.

What these cover that the unit tests cannot: the four controls in
`adapters/sql/engine.py` are all properties of SQLite rather than of our code —
the authorizer is a hook SQLite calls, the deadline is a progress handler SQLite
consults, the statement splitter is `sqlite3.complete_statement`, and the query
plan is the planner's own output. A fake could assert any of them and prove
nothing.

The case worth reading first is
`test_an_answer_is_run_against_a_fresh_database_every_time`: that is the
idempotence property ADR 0013 makes load-bearing, and the one defect a drill
engine built on a database file would have shipped.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.sql import DrillSeedError, run_answer, split_statements
from tests.integration.sql.conftest import SEED

if TYPE_CHECKING:
    from tests.integration.sql.conftest import Runner

PER_CUSTOMER = """\
SELECT c.name, COUNT(o.id) AS orders
  FROM customers c
  LEFT JOIN orders o ON o.customer_id = c.id
 GROUP BY c.id
 ORDER BY c.name;
"""


class TestRunningAnAnswer:
    def test_it_reports_the_rows_the_answer_returned(self, answered: Runner) -> None:
        result = answered(PER_CUSTOMER).result()

        assert result is not None
        assert result.columns == ("name", "orders")
        assert result.rows == (("alice", 2), ("bob", 0), ("carol", 1))

    def test_a_null_comes_back_as_none_for_the_domain_to_spell(
        self, answered: Runner
    ) -> None:
        """The port returns what SQLite gave; `as_text` decides it reads `NULL`.

        Asserted here rather than only in the domain because it is the seam: a
        driver that stringified on the way out would make the domain's rule
        unreachable and nothing in the unit tests would notice.
        """
        result = answered("SELECT name, city FROM customers ORDER BY id;").result()

        assert result is not None
        assert result.rows[1] == ("bob", None)

    def test_an_answer_that_returns_nothing_has_no_result(
        self, answered: Runner
    ) -> None:
        query = answered("UPDATE orders SET status = 'shipped';")

        assert query.result() is None
        assert query.error() is None

    def test_the_last_row_returning_statement_is_the_one_graded(
        self, answered: Runner
    ) -> None:
        """A `CREATE TEMP VIEW` then a `SELECT` over it is a legitimate answer."""
        result = answered(
            "CREATE TEMP VIEW shipped AS SELECT * FROM orders WHERE status='shipped';"
            "\nSELECT COUNT(*) AS n FROM shipped;"
        ).result()

        assert result is not None
        assert result.rows == ((2,),)

    def test_an_answer_written_on_one_line_runs_and_is_graded(
        self, held: Runner
    ) -> None:
        """The same answer as above with the newline taken out, which used to
        run no statements at all.

        Driven through `run_answer` rather than `split_statements` because the
        splitter was only half the failure: the concatenation reached
        `connection.execute`, which refused it at prepare time, so the verdict
        carried a SQLite error about correct SQL and the database was never
        touched. Both halves have to be true -- it parses as two, and both take
        effect.
        """
        query = held(
            "DELETE FROM orders WHERE status = 'pending'; "
            "SELECT COUNT(*) AS n FROM orders;"
        )
        result = query.result()

        assert query.error() is None
        assert len(query.statements()) == 2
        assert result is not None
        assert result.rows == ((2,),)
        table = query.table("orders")
        assert table is not None
        assert table.row_count == 2

    def test_a_syntax_error_is_reported_not_raised(self, answered: Runner) -> None:
        """The most ordinary thing a solver does, and it has to arrive as a
        message rather than a traceback.
        """
        query = answered("SELECT name FORM customers;")
        error = query.error()

        assert query.result() is None
        assert error is not None
        assert 'near "customers"' in error or "FORM" in error

    def test_statements_before_a_failure_have_still_taken_effect(
        self, held: Runner
    ) -> None:
        """The honest thing to grade: that is the state SQLite was left in, and a
        drill asserting on a table will report it.
        """
        query = held("DELETE FROM orders WHERE id = 1;\nSELECT nope FROM orders;")

        assert query.error() is not None
        table = query.table("orders")
        assert table is not None
        assert table.row_count == 2

    def test_the_answer_is_reported_as_the_statements_it_was_split_into(
        self, answered: Runner
    ) -> None:
        query = answered("SELECT 1;\nSELECT 2;")

        assert query.statements() == ("SELECT 1;", "SELECT 2;")


class TestAFreshDatabaseEveryTime:
    def test_an_answer_is_run_against_a_fresh_database_every_time(self) -> None:
        """**The idempotence property, and the reason nothing is kept on disk.**

        ADR 0013 grades on every Ctrl+S, so an answer is run tens of times. An
        `INSERT` against a persistent database gives a different verdict the
        second time; this proves it does not.
        """
        answer = "INSERT INTO orders (customer_id, total, status) VALUES (2, 1.0, 'x');"

        counts = []
        for _ in range(3):
            query = run_answer(seed=SEED, answer=answer, timeout_seconds=5.0)
            table = query.table("orders")
            assert table is not None
            counts.append(table.row_count)
            query.close()

        assert counts == [4, 4, 4]

    def test_an_update_is_idempotent_across_passes_too(self) -> None:
        """The case an `INSERT` does not cover: doubling a column is wrong on the
        second pass even if the row count is not.
        """
        answer = "UPDATE orders SET total = total * 2;"

        totals = []
        for _ in range(2):
            query = run_answer(seed=SEED, answer=answer, timeout_seconds=5.0)
            result = query.table("orders")
            assert result is not None
            totals.append(result.column("total"))
            query.close()

        assert totals[0] == totals[1] == (21.0, 8.0, 14.5)


class TestThePolicy:
    def test_attaching_another_database_is_denied_by_sqlite_itself(
        self, answered: Runner
    ) -> None:
        """The one thing an in-memory database could otherwise do that reaches
        the filesystem. Denied by `set_authorizer`, not by matching the text.
        """
        query = answered("ATTACH DATABASE 'stolen.db' AS evil;")
        error = query.error()

        assert error is not None
        assert "not authorized" in error

    @pytest.mark.parametrize(
        "spelling",
        [
            "ATTACH DATABASE 'x.db' AS e;",
            "attach database 'x.db' as e;",
            "ATTACH/**/DATABASE 'x.db' AS e;",
            "ATTACH\n  DATABASE 'x.db' AS e;",
        ],
    )
    def test_no_spelling_of_attach_gets_through(
        self, answered: Runner, spelling: str
    ) -> None:
        """Why the authorizer rather than a regular expression. Each of these
        defeats a pattern somebody would have written, and a pattern strict
        enough to catch them starts refusing the word inside a string literal.
        """
        assert answered(spelling).error() is not None

    def test_the_word_attach_inside_a_string_literal_is_fine(
        self, answered: Runner
    ) -> None:
        """The other half of the same argument: this is a correct answer, and a
        regular expression over the text would have refused it.
        """
        query = answered("SELECT 'ATTACH DATABASE' AS note;")

        assert query.error() is None
        assert query.result() is not None

    def test_dropping_a_table_is_allowed_because_it_is_a_wrong_answer(
        self, held: Runner
    ) -> None:
        """Not a security problem. `table_exists` reports it, and refusing the
        statement would turn a gradeable mistake into a refusal that teaches
        nothing.
        """
        query = held("DROP TABLE orders;")

        assert query.error() is None
        assert "orders" not in query.tables()

    def test_a_runaway_query_is_stopped_by_the_deadline(self) -> None:
        """A recursive CTE with no base case, which is the only thing this bound
        ever catches in a drill over tens of rows.
        """
        runaway = (
            "WITH RECURSIVE c(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM c) "
            "SELECT COUNT(*) FROM c;"
        )

        query = run_answer(seed=SEED, answer=runaway, timeout_seconds=0.25)
        error = query.error()

        assert error is not None
        assert "interrupted" in error
        query.close()

    def test_the_deadline_is_disarmed_before_the_assertions_read_the_database(
        self,
    ) -> None:
        """The bug the `finally` in `_execute` exists for.

        A slow answer uses the whole budget; if the progress handler were left
        armed, the trusted queries behind `tables()` and `table()` would then
        abort, and a correct-but-slow answer would be reported as having no
        tables at all.
        """
        runaway = (
            "WITH RECURSIVE c(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM c) "
            "SELECT COUNT(*) FROM c;"
        )

        query = run_answer(seed=SEED, answer=runaway, timeout_seconds=0.25)

        assert query.tables() == {"customers", "orders"}
        assert query.table("orders") is not None
        query.close()


class TestTheQueryPlan:
    def test_a_plan_over_an_indexed_lookup_says_search(self, answered: Runner) -> None:
        plan = answered("SELECT * FROM orders WHERE customer_id = 1;").plan()

        assert any("SEARCH" in line for line in plan)
        assert any("idx_orders_customer" in line for line in plan)

    def test_a_plan_over_an_unindexed_filter_says_scan(self, answered: Runner) -> None:
        """The two halves of the advisory this kind exists for, on the same seed:
        identical shapes of query, and SQLite says which one does the work.
        """
        plan = answered("SELECT * FROM orders WHERE status = 'shipped';").plan()

        assert any("SCAN" in line for line in plan)

    def test_the_plan_is_over_the_final_statement(self, answered: Runner) -> None:
        plan = answered(
            "SELECT * FROM customers;\nSELECT * FROM orders WHERE customer_id = 1;"
        ).plan()

        assert any("orders" in line for line in plan)
        assert not any("customers" in line for line in plan)

    def test_an_answer_that_failed_has_no_plan(self, answered: Runner) -> None:
        assert answered("SELECT nope FROM orders;").plan() == ()

    def test_an_empty_answer_has_no_plan(self, answered: Runner) -> None:
        assert answered("-- I will do this later\n").plan() == ()


class TestSplittingStatements:
    def test_it_splits_on_statement_boundaries(self) -> None:
        assert split_statements("SELECT 1;\nSELECT 2;") == ("SELECT 1;", "SELECT 2;")

    def test_a_semicolon_in_a_string_literal_is_not_a_boundary(self) -> None:
        """Why this is `sqlite3.complete_statement` and not `split(';')`."""
        sql = "SELECT 'a;b' AS s;"

        assert split_statements(sql) == ("SELECT 'a;b' AS s;",)

    def test_a_trailing_statement_with_no_semicolon_is_kept(self) -> None:
        """A solver who left the last `;` off meant the statement, and SQLite
        will run it.
        """
        assert split_statements("SELECT 1") == ("SELECT 1",)

    def test_a_multi_line_statement_stays_one_statement(self) -> None:
        sql = "SELECT name\n  FROM customers\n WHERE id = 1;"

        assert len(split_statements(sql)) == 1

    @pytest.mark.parametrize(
        "sql", ["", "\n\n", "-- nothing here\n", "-- one\n-- two\n", ";\n"]
    )
    def test_comments_and_blanks_are_not_statements(self, sql: str) -> None:
        """A stub ships with `-- your answer here`, and counting it as a
        statement would give `sql_matches` a line that is not SQL to search.
        """
        assert split_statements(sql) == ()

    def test_two_statements_on_one_line_are_two_statements(self) -> None:
        """The boundary is a semicolon, not a line ending.

        This split on lines until it was found by reading it: both statements
        came back as one string, `connection.execute` refused it with "You can
        only execute one statement at a time", and a correct answer was graded
        as broken SQL with its first statement never applied.
        """
        sql = "DELETE FROM t WHERE a = 1; SELECT * FROM t;"

        assert split_statements(sql) == (
            "DELETE FROM t WHERE a = 1;",
            "SELECT * FROM t;",
        )

    def test_a_semicolon_in_a_trailing_comment_is_not_a_boundary(self) -> None:
        """Asking at every semicolon means asking inside comments too, and
        `complete_statement` is what knows the difference.
        """
        sql = "SELECT 1 -- what about ; this\n;"

        assert len(split_statements(sql)) == 1

    def test_a_trigger_body_is_one_statement(self) -> None:
        """The case a naive `split(';')` cannot survive and this one must: the
        semicolons inside `BEGIN ... END` are not boundaries, which
        `sqlite3_complete` tracks and nothing in this module does.
        """
        sql = (
            "CREATE TRIGGER t AFTER INSERT ON orders BEGIN "
            "UPDATE totals SET n = n + 1; END;"
        )

        assert split_statements(sql) == (sql,)


class TestABrokenSeed:
    def test_a_seed_that_will_not_run_is_an_exception_not_a_verdict(self) -> None:
        """An authoring bug, so it raises -- the same line `KataRunnerError`
        draws. A solver cannot act on "this exercise's schema is broken".
        """
        with pytest.raises(DrillSeedError, match="seed could not be run"):
            run_answer(seed="CREATE TABLE (;", answer="SELECT 1;", timeout_seconds=5.0)

    def test_a_broken_seed_leaves_no_connection_open(self) -> None:
        """The database is closed on the way out, because the caller never gets
        the object it would have closed.
        """
        for _ in range(50):
            with pytest.raises(DrillSeedError):
                run_answer(
                    seed="NOT SQL AT ALL", answer="SELECT 1;", timeout_seconds=5.0
                )
