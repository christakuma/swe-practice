"""A seeded drill, run for real. No workspace, no subprocess, no files.

The whole reason the drill engine's integration tests are cheap: the engine
builds its database in `:memory:` from the seed text, so an "integration" test
here is a real SQLite connection with a real query planner and still costs under
a millisecond. The kata engine's equivalent costs ten seconds per case because
pytest is a subprocess.

**Two fixtures, and the difference between them is the lifetime split**
`adapters/sql/__init__.py` describes. `answered` hands back a *closed* query, so
a case using it can only read what was computed while the answer ran — which is
the point: a method that had secretly become a live query would raise there
instead of passing. `held` keeps the database open, for the cases that ask
`table()` or `tables()`.
"""

from __future__ import annotations

from contextlib import closing
from typing import TYPE_CHECKING, Protocol

import pytest

from practice.adapters.sql import run_answer

if TYPE_CHECKING:
    from collections.abc import Iterator

    from practice.adapters.sql import SqliteDrillQuery

#: Two cities, three orders, one customer with none -- which is the shape every
#: join lesson needs and the smallest database that can tell an inner join from
#: an outer one. A `NULL` city, because how `NULL` compares is a decision
#: `domain/drills/evaluation.py` makes and a seed with no nulls cannot test it.
#: An index on `orders(customer_id)`, because `query_plan_matches` has nothing
#: to say about a database where every plan is a scan.
SEED = """\
CREATE TABLE customers (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL,
    city    TEXT
);
CREATE TABLE orders (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    total       REAL NOT NULL,
    status      TEXT NOT NULL
);
CREATE INDEX idx_orders_customer ON orders(customer_id);

INSERT INTO customers (id, name, city) VALUES
    (1, 'alice', 'leeds'),
    (2, 'bob',   NULL),
    (3, 'carol', 'york');

INSERT INTO orders (id, customer_id, total, status) VALUES
    (1, 1, 10.5, 'shipped'),
    (2, 1,  4.0, 'pending'),
    (3, 3,  7.25, 'shipped');
"""


class Runner(Protocol):
    """What both fixtures hand back. A protocol so mypy checks the call sites."""

    def __call__(
        self, answer: str, *, seed: str = ..., timeout: float = ...
    ) -> SqliteDrillQuery: ...


@pytest.fixture
def answered() -> Runner:
    """Run an answer, then close the database before returning the query."""

    def go(answer: str, *, seed: str = SEED, timeout: float = 5.0) -> SqliteDrillQuery:
        with closing(
            run_answer(seed=seed, answer=answer, timeout_seconds=timeout)
        ) as query:
            return query

    return go


@pytest.fixture
def held() -> Iterator[Runner]:
    """Run an answer and keep the database open until the test ends.

    Every query it hands out is closed on teardown, so a test cannot leak an
    in-memory database into the next one -- which would not corrupt anything,
    but would quietly let a `tables()` assertion pass against the wrong
    connection.
    """
    opened: list[SqliteDrillQuery] = []

    def go(answer: str, *, seed: str = SEED, timeout: float = 5.0) -> SqliteDrillQuery:
        query = run_answer(seed=seed, answer=answer, timeout_seconds=timeout)
        opened.append(query)
        return query

    yield go
    for query in opened:
        query.close()
