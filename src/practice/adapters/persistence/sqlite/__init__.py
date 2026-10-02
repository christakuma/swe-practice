"""SQLite persistence: hand-written SQL, explicit mappers, no ORM (ADR 0006).

The package is deliberately small modules rather than one file per aggregate
with its own connection logic:

* `connection` — the `Database`, and the numbered migration runner.
* `mappers` — domain <-> row, both directions, with no SQL in sight.
* `attempts` — `SqliteAttemptRepository`, and the SQL it runs.

`reviews` joins them in the next commit.

The split between `mappers` and the repositories is the one worth pointing at,
because it is what decides the testing. A mapper is a pure function over a
`Mapping` — it never sees a connection — so the translation that is easiest to get
subtly wrong is unit-tested in milliseconds, and what is left in a repository is
SQL, which is tested against real SQLite because that is the only thing that can
confirm it.
"""

from practice.adapters.persistence.sqlite.attempts import SqliteAttemptRepository
from practice.adapters.persistence.sqlite.connection import (
    Database,
    Migration,
    MigrationError,
    load_migrations,
)

__all__ = [
    "Database",
    "Migration",
    "MigrationError",
    "SqliteAttemptRepository",
    "load_migrations",
]
