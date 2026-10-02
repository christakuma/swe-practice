"""Shared pytest configuration.

Two things, and they are here rather than anywhere else for the same reason: a
rule that has to be remembered per test is a rule that will be forgotten by one.

**Markers are applied by directory.** The alternative — a decorator on every test
— means a forgotten marker silently drops a test out of every `-m` selector,
which is the one failure mode a marker scheme must not have. Explicit markers
still work and are additive.

**Every test gets its own database, whether it asks for one or not.** From Phase
6, `build_services()` with no arguments builds repositories over
`config.database_path()`, which on a developer's machine is their real attempt
history. A single test that forgot to override it would write into it, and
`practice attempts` would then list test fixtures as real attempts. An autouse
fixture is the only form of this rule that cannot be forgotten — the override is
not something a test opts into.
"""

from __future__ import annotations

from itertools import count
from typing import TYPE_CHECKING

import pytest

from practice.config import DATABASE_PATH_ENV

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

#: A counter rather than the test's node id, because a node id has to be
#: sanitised into a path and a parametrised one is long enough to matter on
#: Windows. Nothing reads it back, so it only has to be unique within the run.
_databases = count()


@pytest.fixture(autouse=True)
def _own_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Point `config.database_path()` at a file this test alone can reach.

    A *path* under pytest's own base temp directory rather than a created
    directory, so a test that never opens a database costs nothing — which is
    almost all of them, since `Database` connects on first use. The parent is
    created by the connection, not here.
    """
    base = tmp_path_factory.getbasetemp() / "db" / str(next(_databases))
    monkeypatch.setenv(DATABASE_PATH_ENV, str(base / "practice.db"))


# Directory under tests/ -> marker applied to everything beneath it.
_MARKER_BY_DIRECTORY = {
    "unit": "unit",
    "integration": "integration",
    "content": "content",
    "web": "web",
    "e2e": "e2e",
}


def pytest_collection_modifyitems(
    config: pytest.Config,
    items: Iterable[pytest.Item],
) -> None:
    tests_root: Path = config.rootpath / "tests"
    for item in items:
        try:
            relative = item.path.relative_to(tests_root)
        except ValueError:  # a test collected from outside tests/
            continue
        if not relative.parts:
            continue
        marker = _MARKER_BY_DIRECTORY.get(relative.parts[0])
        if marker is not None:
            item.add_marker(marker)
