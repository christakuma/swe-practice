"""SQLite persistence: hand-written SQL, explicit mappers, no ORM (ADR 0006).

The package is deliberately small modules rather than one file per aggregate
with its own connection logic. `connection` holds the `Database` and the
numbered migration runner; `mappers` and the two repositories join it in this
phase's next commits.

The split between a mapper and a repository is the one worth pointing at ahead
of time, because it is what decides the testing. A mapper will be a pure
function over a `Mapping` — it never sees a connection — so the translation that
is easiest to get subtly wrong is unit-tested in milliseconds, and what is left
in a repository is SQL, which is tested against real SQLite because that is the
only thing that can confirm it.
"""

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
    "load_migrations",
]
