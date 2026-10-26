"""Settings in SQLite: one row per key, replaced on write.

Satisfies `practice.domain.ports.SettingsRepository`, structurally (ADR 0002).
Upsert rather than insert-or-fail because a setting has no history worth keeping:
the question is only ever what it is now.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from practice.adapters.persistence.sqlite.connection import Database

__all__ = ["SqliteSettingsRepository"]

_UPSERT: Final = (
    "INSERT INTO settings (key, value) VALUES (:key, :value) "
    "ON CONFLICT (key) DO UPDATE SET value = excluded.value"
)


class SqliteSettingsRepository:
    """The user's choices, one text value per key."""

    __slots__ = ("_database",)

    def __init__(self, database: Database) -> None:
        self._database = database

    def get(self, key: str) -> str | None:
        with self._database.connect() as connection:
            row = connection.execute(
                "SELECT value FROM settings WHERE key = :key", {"key": key}
            ).fetchone()
        return str(row[0]) if row is not None else None

    def set(self, key: str, value: str) -> None:
        with self._database.connect() as connection:
            connection.execute(_UPSERT, {"key": key, "value": value})

    def delete(self, key: str) -> None:
        with self._database.connect() as connection:
            connection.execute("DELETE FROM settings WHERE key = :key", {"key": key})

    def __repr__(self) -> str:
        return f"SqliteSettingsRepository({self._database.path})"
