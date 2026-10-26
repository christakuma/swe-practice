"""`SettingsRepository`, held to one contract by both of its implementations.

PLAN.md §13 wants a port to have two implementations; running the same
assertions against the SQLite one and the in-memory one is what shows they are
the same port rather than two things that happen to share a name.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.persistence import (
    Database,
    InMemorySettingsRepository,
    SqliteSettingsRepository,
)

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.ports import SettingsRepository


@pytest.fixture(params=["memory", "sqlite"])
def settings(request: pytest.FixtureRequest, tmp_path: Path) -> SettingsRepository:
    if request.param == "memory":
        return InMemorySettingsRepository()
    return SqliteSettingsRepository(Database(tmp_path / "practice.db"))


def test_a_key_never_set_is_absent(settings: SettingsRepository) -> None:
    assert settings.get("reviews_enabled") is None


def test_a_value_reads_back(settings: SettingsRepository) -> None:
    settings.set("reviews_enabled", "0")

    assert settings.get("reviews_enabled") == "0"


def test_setting_again_replaces(settings: SettingsRepository) -> None:
    settings.set("goal:systems", "2026-12-01")
    settings.set("goal:systems", "2026-12-24")

    assert settings.get("goal:systems") == "2026-12-24"


def test_delete_forgets_and_tolerates_a_missing_key(
    settings: SettingsRepository,
) -> None:
    settings.set("goal:systems", "2026-12-01")

    settings.delete("goal:systems")
    settings.delete("goal:systems")

    assert settings.get("goal:systems") is None


def test_keys_are_independent(settings: SettingsRepository) -> None:
    settings.set("a", "1")
    settings.set("b", "2")
    settings.delete("a")

    assert settings.get("b") == "2"


def test_each_repository_describes_itself(tmp_path: Path) -> None:
    sqlite = SqliteSettingsRepository(Database(tmp_path / "practice.db"))

    assert "practice.db" in repr(sqlite)
    assert "0 keys" in repr(InMemorySettingsRepository())
