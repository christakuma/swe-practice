"""The SQL drill engine: a seed, an answer, and a `DrillQuery` over the result.

The third exercise kind's adapter (PLAN.md §11, Phase 14), and the second
package in the project allowed to import `sqlite3` — see
`tests/unit/test_architecture.py`, where the rule that used to say *only the
persistence adapter speaks SQLite* now says which two do and why each one does.

The split between the modules is by lifetime, the same way
`adapters/sandbox/workspace.py` splits:

* `engine.py` runs things. It owns the four controls that make running an
  untrusted answer safe — an in-memory database, SQLite's own authorizer, a
  wall-clock deadline, and statement splitting that is not a `split(";")`.
* `drill_query.py` answers questions. It holds the connection the engine left
  open, because `table()` and `tables()` are questions about a live database.
* `grader.py` turns the answers into a verdict, and satisfies `Grader` for
  `ExerciseKind.SQL_DRILL`.

There is no `SqlDrillRunner` protocol between the grader and the engine, and
that is deliberate rather than an omission. `KataRunner` exists because a pytest
subprocess costs ten seconds and the grader's *mapping* had to be testable
without one; running a drill costs under a millisecond, so the grader can be
tested against the real engine and a protocol here would be the abstraction §13
says to delete.
"""

from practice.adapters.sql.drill_query import SqliteDrillQuery
from practice.adapters.sql.engine import DrillSeedError, run_answer, split_statements
from practice.adapters.sql.grader import (
    ANSWER_CHECK_ID,
    SqlDrillGrader,
    SqlDrillGraderError,
)

__all__ = [
    "ANSWER_CHECK_ID",
    "DrillSeedError",
    "SqlDrillGrader",
    "SqlDrillGraderError",
    "SqliteDrillQuery",
    "run_answer",
    "split_statements",
]
