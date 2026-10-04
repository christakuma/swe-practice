"""The connection and the migration runner, against real SQLite.

Integration tests, and they have to be: every claim here — WAL is on, foreign
keys are enforced, a failed migration leaves nothing behind, the shipped schema
applies from empty — is a claim about what SQLite does, and a fake database
would let all four pass while being false.

The one thing deliberately asserted *without* a database is that constructing a
`Database` creates nothing. That is the property `composition.py` depends on, and
the one a lazily-opened connection exists to provide.
"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from typing import TYPE_CHECKING

import pytest

from practice.adapters.persistence.sqlite import (
    Database,
    Migration,
    MigrationError,
    load_migrations,
)
from practice.adapters.persistence.sqlite.connection import MIGRATIONS_DIR

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def database(tmp_path: Path) -> Database:
    """Under a directory that does not exist yet, so creation is observable."""
    return Database(tmp_path / "state" / "practice.db")


def tables(database: Database) -> set[str]:
    with database.connect() as connection:
        return {
            str(row["name"])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }


# --- laziness --------------------------------------------------------------


def test_constructing_a_database_touches_nothing(tmp_path: Path) -> None:
    """What `build_services` relies on: wiring the graph must not create storage.

    `practice validate` builds every adapter and never reads a row, and a
    database file appearing in the user's data directory because someone
    validated the content library would be a side effect with no cause anyone
    could see.
    """
    path = tmp_path / "state" / "practice.db"

    database = Database(path)

    assert database.exists is False
    assert not path.parent.exists()


def test_the_first_connection_creates_the_file_and_its_directory(
    database: Database,
) -> None:
    with database.connect() as connection:
        connection.execute("SELECT 1")

    assert database.exists is True


# --- what every connection is configured with ------------------------------


def test_write_ahead_logging_is_on(database: Database) -> None:
    """Persistent in the database header, so this also proves the pragma ran at
    least once rather than that it runs every time.
    """
    with database.connect() as connection:
        mode = connection.execute("PRAGMA journal_mode").fetchone()[0]

    assert str(mode).lower() == "wal"


def test_foreign_keys_are_enforced(database: Database) -> None:
    """Off by default and per-connection, which is why it is set in code rather
    than in a migration — and why it is worth a test that a real constraint
    actually fires.
    """
    with database.connect() as connection:
        connection.execute("CREATE TABLE parent (id TEXT PRIMARY KEY) STRICT")
        connection.execute("CREATE TABLE child (id TEXT REFERENCES parent (id)) STRICT")

    with (
        pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"),
        database.connect() as connection,
    ):
        connection.execute("INSERT INTO child VALUES ('orphan')")


def test_rows_come_back_addressable_by_column_name(database: Database) -> None:
    """`sqlite3.Row`, so a mapper reads `row["started_at"]` rather than `row[3]`.

    Not cosmetic: positional access is how a mapper silently starts reading the
    wrong column the first time a migration adds one in the middle.
    """
    with database.connect() as connection:
        row = connection.execute("SELECT 1 AS answer").fetchone()

    assert row["answer"] == 1


# --- transactions ----------------------------------------------------------


def test_a_connection_commits_on_a_clean_exit(database: Database) -> None:
    with database.connect() as connection:
        connection.execute("CREATE TABLE note (text TEXT NOT NULL) STRICT")
        connection.execute("INSERT INTO note VALUES ('kept')")

    with database.connect() as connection:
        assert connection.execute("SELECT text FROM note").fetchone()["text"] == "kept"


def test_a_connection_rolls_back_when_the_block_raises(database: Database) -> None:
    """One transaction per operation is only worth having if it unwinds.

    Saving an attempt deletes its event rows and reinserts them, so a failure
    halfway through without this would leave an attempt whose log has been
    truncated — strictly worse than a save that did not happen.
    """
    with database.connect() as connection:
        connection.execute("CREATE TABLE note (text TEXT NOT NULL) STRICT")

    with (  # noqa: PT012  (two statements, and the second one is the point)
        pytest.raises(RuntimeError, match="interrupted"),
        database.connect() as connection,
    ):
        connection.execute("INSERT INTO note VALUES ('doomed')")
        raise RuntimeError("interrupted")

    with database.connect() as connection:
        assert connection.execute("SELECT count(*) AS n FROM note").fetchone()["n"] == 0


# --- the shipped schema ----------------------------------------------------


def test_the_shipped_migrations_apply_from_empty(database: Database) -> None:
    database.migrate()

    assert {"attempts", "attempt_events", "review_cards"} <= tables(database)


def test_migrating_twice_applies_nothing_the_second_time(tmp_path: Path) -> None:
    """The property that makes it safe to call on every startup. Asserted through
    two `Database` objects over one file, because a single one short-circuits on
    its own flag and would prove only that the flag works.

    Against `load_migrations()` rather than a literal `[1]`, which is what it was
    until Phase 13 shipped 0002 and this failed as the only test that had to
    change. The claim is *each migration is recorded exactly once*, and a list
    written out by hand states it for one history and then stops being a test of
    anything the next time the schema moves.
    """
    expected = [migration.version for migration in load_migrations()]
    path = tmp_path / "practice.db"
    Database(path).migrate()

    Database(path).migrate()

    with Database(path).connect() as connection:
        rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    assert [int(row["version"]) for row in rows] == expected


def test_a_second_migration_is_applied_to_an_existing_database(
    tmp_path: Path,
) -> None:
    """The case `CREATE TABLE IF NOT EXISTS` cannot cover.

    A migration that adds a column has no idempotent spelling, so the runner has
    to decide what to apply from the recorded version. This is that decision,
    with a second migration that would fail if it ran twice.
    """
    path = tmp_path / "practice.db"
    first = Migration(version=1, name="one", sql="CREATE TABLE a (x TEXT) STRICT;")
    second = Migration(version=2, name="two", sql="ALTER TABLE a ADD COLUMN y TEXT;")

    Database(path, migrations=[first]).migrate()
    Database(path, migrations=[first, second]).migrate()

    with Database(path, migrations=[first, second]).connect() as connection:
        columns = connection.execute("PRAGMA table_info(a)").fetchall()
    assert [str(row["name"]) for row in columns] == ["x", "y"]


def test_a_failing_migration_leaves_the_database_untouched(tmp_path: Path) -> None:
    """Each migration is one transaction, so a half-applied schema is impossible.

    Worth proving rather than assuming: `executescript` commits any pending
    transaction under the driver's legacy transaction mode, and this is the test
    that would catch a future change back to it.
    """
    path = tmp_path / "practice.db"
    broken = Migration(
        version=1,
        name="broken",
        sql="CREATE TABLE a (x TEXT) STRICT;\nTHIS IS NOT SQL;\n",
    )

    with pytest.raises(sqlite3.Error):
        Database(path, migrations=[broken]).migrate()

    # `closing`, not a bare `with`: a sqlite3 connection's context manager
    # commits and does *not* close, and an unclosed connection surfaces later as
    # an unraisable-exception warning against whichever test the collector
    # happens to be running. Found exactly that way.
    with closing(sqlite3.connect(path)) as raw:
        names = {
            str(row[0])
            for row in raw.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert "a" not in names


def test_a_database_from_a_newer_practice_is_refused(tmp_path: Path) -> None:
    """Downgrading is the one migration direction that cannot be guessed at.

    A database carrying version 2 against a build that ships only version 1 was
    written by something that knew more about the schema than this process does.
    Applying nothing and carrying on would read rows through a mapper that does
    not match them.
    """
    path = tmp_path / "practice.db"
    first = Migration(version=1, name="one", sql="CREATE TABLE a (x TEXT) STRICT;")
    second = Migration(version=2, name="two", sql="ALTER TABLE a ADD COLUMN y TEXT;")
    Database(path, migrations=[first, second]).migrate()

    with pytest.raises(MigrationError, match="newer"):
        Database(path, migrations=[first]).migrate()


# --- loading the migration directory ---------------------------------------


def test_the_shipped_directory_loads_in_version_order() -> None:
    found = load_migrations(MIGRATIONS_DIR)

    assert [migration.version for migration in found] == list(range(1, len(found) + 1))
    assert found[0].name == "initial"
    assert found[0].filename == "0001_initial.sql"


def test_no_shipped_migration_manages_its_own_transaction() -> None:
    """The runner wraps each file in one transaction, so a `BEGIN` inside one
    would commit half of it. Cheap to check, and invisible if it ever happens.
    """
    for migration in load_migrations(MIGRATIONS_DIR):
        lowered = migration.sql.lower()
        assert "begin;" not in lowered, migration.filename
        assert "commit;" not in lowered, migration.filename


def test_a_gap_in_the_numbering_is_refused(tmp_path: Path) -> None:
    """One of two things, and both mean a fresh install gets a different schema
    from the machine the change was tested on: a deleted file, or a merge that
    dropped one. Neither is visible on an already-migrated database.
    """
    (tmp_path / "0001_one.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "0003_three.sql").write_text("SELECT 1;", encoding="utf-8")

    with pytest.raises(MigrationError, match="no gaps"):
        load_migrations(tmp_path)


def test_two_files_with_the_same_number_are_refused(tmp_path: Path) -> None:
    """What two branches each adding `0002_` produces. The message names both
    files, because the fix is to renumber one and only a human can pick which.
    """
    (tmp_path / "0001_one.sql").write_text("SELECT 1;", encoding="utf-8")
    (tmp_path / "001_one.sql").write_text("SELECT 1;", encoding="utf-8")

    with pytest.raises(MigrationError, match="numbered 0001"):
        load_migrations(tmp_path)


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("initial.sql", "not named"),
        ("0001_.sql", "not named"),
        ("abcd_initial.sql", "version number"),
        ("0000_initial.sql", "versions start at 1"),
    ],
)
def test_a_misnamed_migration_says_what_the_name_should_look_like(
    tmp_path: Path, name: str, expected: str
) -> None:
    (tmp_path / name).write_text("SELECT 1;", encoding="utf-8")

    with pytest.raises(MigrationError, match=expected):
        load_migrations(tmp_path)


def test_an_empty_directory_is_a_valid_empty_history(tmp_path: Path) -> None:
    """Not an error: it is what a `Database` injected with no migrations at all
    needs to be able to mean, and the tests above rely on it.
    """
    assert load_migrations(tmp_path) == ()
