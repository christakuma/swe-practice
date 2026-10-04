"""The two `DrillQuery` implementations, asked the same questions.

The drill family's counterpart to `tests/integration/git/test_conformance.py`,
and it exists for the same reason that one does: **the 86 unit tests under
`tests/unit/domain/drills/` are evidence about the real engine only if the fake
they run against answers the way the real engine does.** Without this file they
are evidence about `FakeDrillQuery`, which nothing ships.

The shape is the one that file established. Each case states a database and an
answer, builds both implementations over it — the real one by running the SQL,
the fake one by being *told* the rows — and asserts they agree. A fake that
drifted would fail here rather than silently making a hundred tests meaningless.

**What is deliberately not conformed.** `statements()` and `plan()` are
pass-through on both sides (the engine computes them, the fake is handed them),
so a case asserting the two agree would be asserting that a tuple equals itself.
`error()` is likewise verbatim. The methods worth conforming are the four with
*derivation* in them: how a result set is built from a cursor, how `column`
finds a column, which names count as tables, and what row and column order a
table comes back in.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.domain.ports import ResultSet
from tests.fakes.drill import FakeDrillQuery
from tests.integration.sql.conftest import SEED

if TYPE_CHECKING:
    from practice.domain.ports import DrillQuery
    from tests.integration.sql.conftest import Runner


def mirror(query: DrillQuery, *tables: str) -> FakeDrillQuery:
    """A fake built to describe exactly what the real query reports.

    This is the whole mechanism: if the fake can be constructed from the real
    one's answers and then agree with it, the two have the same observable
    behaviour. The tables have to be named because `DrillQuery` has no "every
    table and its rows" method and should not — the assertions ask for one table
    at a time.
    """
    return FakeDrillQuery(
        result=query.result(),
        tables={
            name: table for name in tables if (table := query.table(name)) is not None
        },
        plan=query.plan(),
        statements=query.statements(),
        error=query.error(),
    )


class TestAResultSetIsBuiltTheSameWay:
    @pytest.mark.parametrize(
        "answer",
        [
            "SELECT name, city FROM customers ORDER BY id;",
            "SELECT COUNT(*) AS n FROM orders;",
            "SELECT * FROM orders WHERE 0;",
            "SELECT ROUND(AVG(total), 2) AS avg_total FROM orders;",
            (
                "SELECT c.name, o.total FROM customers c JOIN orders o"
                " ON o.customer_id = c.id ORDER BY o.id;"
            ),
            "SELECT 1 AS a, 1 AS a;",
            "SELECT NULL AS nothing;",
            "SELECT x'00' AS blob;",
        ],
    )
    def test_the_columns_and_rows_agree(self, held: Runner, answer: str) -> None:
        real = held(answer)
        fake = mirror(real)

        assert fake.result() == real.result()

    def test_a_column_is_found_by_name_the_same_way(self, held: Runner) -> None:
        real = held("SELECT name, city FROM customers ORDER BY id;")
        fake = mirror(real)
        theirs, ours = real.result(), fake.result()

        assert theirs is not None
        assert ours is not None
        assert ours.column("city") == theirs.column("city")

    def test_a_repeated_column_name_resolves_the_same_way(self, held: Runner) -> None:
        """`SELECT a.id, b.id` is legal SQL, and both sides must take the first.

        This is the case a mapping-based result set could not have expressed at
        all, which is why `ResultSet.rows` is positional.
        """
        real = held("SELECT id AS id, customer_id AS id FROM orders ORDER BY id;")
        fake = mirror(real)
        theirs, ours = real.result(), fake.result()

        assert theirs is not None
        assert ours is not None
        assert theirs.columns == ("id", "id")
        assert ours.column("id") == theirs.column("id")


class TestTablesAgree:
    def test_both_report_the_same_table_names(self, held: Runner) -> None:
        real = held("SELECT 1;")
        fake = mirror(real, "customers", "orders")

        assert fake.tables() == real.tables() == frozenset({"customers", "orders"})

    def test_a_view_counts_as_a_table_on_both_sides(self, held: Runner) -> None:
        real = held(
            "CREATE VIEW shipped AS SELECT * FROM orders WHERE status='shipped';"
        )
        fake = mirror(real, "customers", "orders", "shipped")

        assert "shipped" in real.tables()
        assert fake.tables() == real.tables()

    def test_sqlites_own_bookkeeping_is_not_a_table_on_either_side(
        self, held: Runner
    ) -> None:
        """`sqlite_sequence` appears the moment a drill uses `AUTOINCREMENT`, and
        an internal name in a `table_exists` failure message is noise in the one
        message that has to be readable.
        """
        real = held(
            "CREATE TABLE t (id INTEGER PRIMARY KEY AUTOINCREMENT);"
            "\nINSERT INTO t DEFAULT VALUES;"
        )

        assert not any(name.startswith("sqlite_") for name in real.tables())
        assert mirror(real, "t").tables() == frozenset({"t"})

    def test_a_table_that_is_not_there_is_none_on_both_sides(
        self, held: Runner
    ) -> None:
        real = held("SELECT 1;")
        fake = mirror(real, "customers")

        assert real.table("nope") is None
        assert fake.table("nope") is None


class TestATablesContentsAgree:
    @pytest.mark.parametrize("name", ["customers", "orders"])
    def test_the_whole_table_agrees(self, held: Runner, name: str) -> None:
        real = held("SELECT 1;")
        fake = mirror(real, name)

        assert fake.table(name) == real.table(name)

    def test_the_state_after_a_destructive_answer_agrees(self, held: Runner) -> None:
        """The case `tables.py` is for: the answer returned nothing, and the
        thing being graded is what is left.
        """
        real = held("DELETE FROM orders WHERE status = 'pending';")
        fake = mirror(real, "orders")

        assert real.result() is None
        assert fake.table("orders") == real.table("orders")
        table = real.table("orders")
        assert table is not None
        assert table.row_count == 2

    def test_rows_come_back_in_rowid_order_on_both_sides(self, held: Runner) -> None:
        """What makes an author's literal rows comparable without the drill
        specifying an `ORDER BY` it never wrote -- so `ordered: true` means
        insertion order, and that has to be true of the real engine.
        """
        real = held(
            "INSERT INTO customers (id, name, city) VALUES (4, 'dave', 'hull');"
        )
        table = real.table("customers")

        assert table is not None
        assert table.column("name") == ("alice", "bob", "carol", "dave")
        assert mirror(real, "customers").table("customers") == table

    def test_columns_come_back_in_declared_order_on_both_sides(
        self, held: Runner
    ) -> None:
        real = held("SELECT 1;")
        table = real.table("orders")

        assert table is not None
        assert table.columns == ("id", "customer_id", "total", "status")

    def test_a_dropped_table_is_gone_on_both_sides(self, held: Runner) -> None:
        real = held("DROP TABLE orders;")
        fake = mirror(real, "customers", "orders")

        assert real.table("orders") is None
        assert fake.table("orders") is None

    def test_a_view_over_a_dropped_table_is_unreadable_rather_than_an_error(
        self, held: Runner
    ) -> None:
        """A state the fake cannot produce by itself and the real engine can.

        The view is still named in `sqlite_master`, so `tables()` reports it, but
        selecting from it raises -- and `table()` has to answer `None` rather
        than let a `sqlite3.Error` out, because a traceback in a verdict panel
        teaches nothing (§6.5). This is the one conformance case that is really
        about the real implementation keeping a promise the fake makes trivially.
        """
        real = held(
            "CREATE VIEW shipped AS SELECT * FROM orders WHERE status='shipped';"
            "\nDROP TABLE orders;"
        )

        assert "shipped" in real.tables()
        assert real.table("shipped") is None


def test_a_quoted_identifier_is_handled_by_the_real_engine(held: Runner) -> None:
    """A table whose name is a reserved word, which is why `table()` quotes.

    Not a conformance case -- the fake is a dict and cannot have this problem --
    but it belongs here rather than in `test_engine.py` because what it defends
    is the one line of string-built SQL in the adapter.
    """
    real = held('CREATE TABLE "order" (id INTEGER, note TEXT);')

    assert "order" in real.tables()
    assert real.table("order") == ResultSet(columns=("id", "note"), rows=())


def test_the_seed_itself_is_what_both_sides_start_from() -> None:
    """A guard on the fixture rather than on the code.

    Every case above builds its fake from the real query, so a seed that had
    quietly stopped creating a table would make them agree about nothing and
    still pass. This is what notices.
    """
    assert "CREATE TABLE customers" in SEED
    assert "CREATE TABLE orders" in SEED
    assert "CREATE INDEX idx_orders_customer" in SEED
