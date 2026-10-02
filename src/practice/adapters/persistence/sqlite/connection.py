"""Opening the database, and bringing its schema up to date.

Two things live here, and they are together because neither is useful alone: the
connection every repository borrows, and the migration runner that guarantees
the tables it queries exist.

**Nothing is opened until something is read or written.** `Database(path)` stores
a path and does nothing else — no connection, no directory, no file. That is a
requirement rather than a nicety: `composition.py` builds the whole object graph
for `practice validate`, which never touches storage, and
`test_building_the_graph_writes_nothing_to_disk` fails if a database file appears
as a side effect of wiring. So migrations run on first use, once per process.

**One connection per operation, inside one explicit transaction.** The
alternative — a long-lived connection held on the `Database` — is faster by an
amount nobody can measure for a local practice tool, and costs the two things
that matter here. `sqlite3` connections are bound to the thread that created
them unless that check is disabled, so a held connection makes the Phase 7 web
app a threading question; and a held connection makes "what is committed" depend
on where the last `commit()` was, which is exactly the class of bug that loses an
attempt. A connection per operation is thread-safe by construction and commits
at a boundary you can point at.

**Transactions are SQL, not driver state.** The connection is opened with
`autocommit=True`, which in Python 3.12+ means the driver does no implicit
transaction management at all, and `connect()` issues `BEGIN IMMEDIATE` /
`COMMIT` itself. Found by running it: `PRAGMA journal_mode=WAL` cannot execute
inside a transaction, so a driver that opens one before the first statement —
which is what `autocommit=False` does — makes the WAL pragma fail on a fresh
database. Explicit SQL puts the pragmas before the transaction and leaves no
doubt about where the boundary is.

`BEGIN IMMEDIATE` rather than a deferred `BEGIN`, including for reads. It takes
the write lock up front, so two writers queue on the lock instead of one
discovering halfway through that it cannot upgrade and failing with
`SQLITE_BUSY`. The cost is that concurrent readers serialise, which for a
single-user tool whose longest query returns a few dozen rows is not a cost.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

__all__ = [
    "MIGRATIONS_DIR",
    "Database",
    "Migration",
    "MigrationError",
    "load_migrations",
]

#: The numbered SQL files, shipped beside this module. Read from the filesystem
#: rather than through `importlib.resources`, for the same reason `config.py`
#: derives the content root from `__file__`: this tool is installed from a
#: source checkout and is not meant to be shipped as a wheel. The kata runner's
#: plugin source is loaded the same way.
MIGRATIONS_DIR: Final = Path(__file__).parent / "migrations"

#: `0001_initial.sql` -> version 1, name `initial`.
_FILENAME_PARTS: Final = 2

#: How long a connection waits for a lock another process holds before giving
#: up. Generous, because the thing on the other side is a second `practice`
#: invocation writing one row, not a report over a million.
_LOCK_TIMEOUT_SECONDS: Final = 5.0

#: Applied to every connection. `foreign_keys` is per-connection and off by
#: default, which is why it is here and not in a migration: the
#: `ON DELETE CASCADE` that keeps an attempt's event log from outliving the
#: attempt is enforced by the connection, not by the schema.
_PRAGMAS: Final = (
    # Persistent, stored in the database header, so this is a no-op after the
    # first connection ever made. Set every time anyway: a database created by
    # some future tool that forgot would otherwise stay in rollback-journal mode
    # silently.
    "PRAGMA journal_mode=WAL",
    "PRAGMA foreign_keys=ON",
    # WAL's durability/ speed trade: a commit is durable against a process
    # crash, and loses the last transactions only if the machine loses power
    # mid-write. For practice attempts that is the right side of the trade.
    "PRAGMA synchronous=NORMAL",
)

_SCHEMA_MIGRATIONS = """\
CREATE TABLE IF NOT EXISTS schema_migrations (
    version    INTEGER PRIMARY KEY NOT NULL,
    name       TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


class MigrationError(Exception):
    """The migrations on disk are not a schema history that can be applied.

    Raised for a gap, a duplicate version, an unparseable filename, or a
    database whose recorded history is ahead of the files. Every one of those
    means the next `migrate()` would do something nobody intended, and the
    honest response is to refuse before touching the database.
    """


@dataclass(frozen=True, slots=True, order=True)
class Migration:
    """One numbered step, as the file on disk spells it."""

    version: int
    name: str
    sql: str

    @property
    def filename(self) -> str:
        return f"{self.version:04d}_{self.name}.sql"


def load_migrations(directory: Path = MIGRATIONS_DIR) -> tuple[Migration, ...]:
    """Every migration in `directory`, in version order.

    Refuses a gap and a duplicate rather than applying what it found. A history
    numbered 1, 2, 4 is one of two things — a file that was deleted, or a merge
    that dropped one — and both of them mean the schema a developer is testing
    against is not the schema a fresh install will get. That divergence is
    invisible on a machine whose database is already migrated, which is exactly
    why it is checked here.
    """
    found: dict[int, Migration] = {}
    for path in sorted(directory.glob("*.sql")):
        version, name = _parse_filename(path)
        if version in found:
            raise MigrationError(
                f"two migrations are numbered {version:04d}: "
                f"{found[version].filename} and {path.name}"
            )
        found[version] = Migration(
            version=version,
            name=name,
            sql=path.read_text(encoding="utf-8"),
        )

    expected = list(range(1, len(found) + 1))
    if sorted(found) != expected:
        raise MigrationError(
            f"migrations must be numbered from 1 with no gaps; "
            f"found {sorted(found)} in {directory}"
        )
    return tuple(found[version] for version in expected)


def _parse_filename(path: Path) -> tuple[int, str]:
    parts = path.stem.split("_", 1)
    if len(parts) != _FILENAME_PARTS or not parts[1]:
        raise MigrationError(
            f"{path.name} is not named <version>_<name>.sql, e.g. 0001_initial.sql"
        )
    try:
        version = int(parts[0])
    except ValueError as exc:
        raise MigrationError(
            f"{path.name} does not start with a version number"
        ) from exc
    if version < 1:
        raise MigrationError(f"{path.name} is numbered below 1; versions start at 1")
    return version, parts[1]


class Database:
    """One SQLite file, migrated on first use.

    Not a repository and not a connection pool: the thing the repositories share
    so that there is one answer to where the database is and whether its schema
    is current.
    """

    __slots__ = ("_migrated", "_migrations", "_path")

    def __init__(
        self, path: Path, *, migrations: Sequence[Migration] | None = None
    ) -> None:
        """`migrations` is injectable so a test can apply a schema of its own.

        Used by the migration tests to build the histories that must be refused,
        without putting a deliberately broken `.sql` file in the shipped
        directory where the next reader would wonder what it was for.
        """
        self._path = path
        self._migrations = tuple(migrations) if migrations is not None else None
        self._migrated = False

    @property
    def path(self) -> Path:
        return self._path

    @property
    def exists(self) -> bool:
        """Whether the file is there. False until something writes to it."""
        return self._path.is_file()

    def migrate(self) -> None:
        """Apply every migration the database has not seen yet.

        Idempotent in both senses that matter: calling it twice in a process is
        free, and running it against an already-migrated database applies
        nothing. The second is what makes it safe to call on every startup, and
        it rests on the recorded version rather than on `CREATE TABLE IF NOT
        EXISTS` — a migration that adds a column has no such spelling, so a
        runner that relied on idempotent DDL would work until the first one did.
        """
        if self._migrated:
            return
        with self._open() as connection:
            self._apply(connection)
        self._migrated = True

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """A migrated, configured connection inside one transaction.

        Commits on a clean exit and rolls back on any exception, including
        `KeyboardInterrupt` — a half-saved attempt is worse than an unsaved one,
        because the log would then disagree with the repository it describes.
        """
        self.migrate()
        with self._open() as connection:
            yield connection

    # --- the pieces --------------------------------------------------------

    @contextmanager
    def _open(self) -> Iterator[sqlite3.Connection]:
        """Open, configure, begin; then commit or roll back, and always close."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            self._path, timeout=_LOCK_TIMEOUT_SECONDS, autocommit=True
        )
        try:
            connection.row_factory = sqlite3.Row
            for pragma in _PRAGMAS:
                connection.execute(pragma)
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
            except BaseException:
                if connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise
            connection.execute("COMMIT")
        finally:
            connection.close()

    def _apply(self, connection: sqlite3.Connection) -> None:
        migrations = (
            self._migrations
            if self._migrations is not None
            else load_migrations(MIGRATIONS_DIR)
        )
        connection.execute(_SCHEMA_MIGRATIONS)
        applied = {
            int(row["version"])
            for row in connection.execute("SELECT version FROM schema_migrations")
        }

        unknown = applied - {migration.version for migration in migrations}
        if unknown:
            raise MigrationError(
                f"{self._path} has migrations {sorted(unknown)} applied that this "
                f"version of practice does not ship; it was written by a newer one"
            )

        for migration in migrations:
            if migration.version in applied:
                continue
            # `executescript` inside an open transaction does not commit it —
            # verified by running it, because the documented behaviour differs
            # between the legacy and the modern transaction modes. So a
            # migration that fails halfway rolls its own DDL back with the
            # transaction, and a migration file must not contain `BEGIN` or
            # `COMMIT` of its own.
            connection.executescript(migration.sql)
            connection.execute(
                "INSERT INTO schema_migrations (version, name, applied_at) "
                "VALUES (?, ?, datetime('now'))",
                (migration.version, migration.name),
            )

    def __repr__(self) -> str:
        return f"Database({self._path})"
