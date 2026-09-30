"""Shared pytest configuration.

Markers are applied by directory rather than by hand. The alternative — a
decorator on every test — means a forgotten marker silently drops a test out of
every `-m` selector, which is the one failure mode a marker scheme must not
have. Explicit markers still work and are additive.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    import pytest

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
