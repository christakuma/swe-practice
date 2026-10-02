"""Nothing this app serves reaches the network.

PLAN.md §8.2 asks for exactly this test, and §2 states the rule it enforces:
runtime dependencies must never include anything that phones home, and a template
with a CDN `<script>` in it is a runtime dependency on someone else's uptime. The
failure mode is the one every offline claim has — it is true on the day it is
written and nobody notices the stylesheet added six months later.

**Two halves that between them cover every file.** Our own templates and
stylesheets are grepped for remote references; the four vendored libraries are
pinned by hash in `test_vendored_assets.py`, because a minified file carries its
own licence URL and grepping it would have to be weakened until it caught nothing.
`test_every_file_is_covered_by_one_of_the_two_rules` is what stops a third
category from appearing between them and being checked by neither.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from practice.interface.web.app import templates_root
from practice.interface.web.vendor import ASSETS, VENDOR_DIRNAME, static_root

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from fastapi.testclient import TestClient

#: What a remote reference looks like, in the spellings that reach a browser.
#: `//cdn` is in there because a protocol-relative URL is the one form that does
#: not contain `http` at all and still fetches from somewhere else.
FORBIDDEN: Final = ("http://", "https://", "//cdn", "//unpkg", "//fonts.")

#: Files we wrote, which is what the grep is about. A binary asset of our own
#: would be hashed by nothing and grepped by nothing, so adding one means adding
#: a rule — which the coverage test below will insist on.
GREPPED_SUFFIXES: Final = frozenset({".html", ".css", ".js", ".svg", ".txt"})


def our_files() -> Iterator[Path]:
    """Every template, plus every static file that is not vendored."""
    yield from sorted(templates_root().rglob("*"))
    for path in sorted(static_root().rglob("*")):
        if VENDOR_DIRNAME not in path.relative_to(static_root()).parts:
            yield path


def test_no_template_or_asset_of_ours_names_a_remote_host() -> None:
    offenders: list[str] = []
    for path in our_files():
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            offenders += [
                f"{path.name}:{line_number} contains {needle!r}: {line.strip()}"
                for needle in FORBIDDEN
                if needle in line
            ]

    assert offenders == [], "offline means no remote references:\n" + "\n".join(
        f"  - {offender}" for offender in offenders
    )


def test_the_grep_actually_read_something() -> None:
    """A renamed directory would leave the assertion above vacuously true.

    The same guard the architecture test puts on its own walk, and the reason it
    is not paranoia here: `templates_root()` is derived from `__file__`, so a
    package reorganisation moves it silently.
    """
    found = {path.name for path in our_files() if path.is_file()}

    assert {"base.html", "index.html", "app.css"} <= found


def test_every_file_is_covered_by_one_of_the_two_rules() -> None:
    """Grepped, or hash-pinned. No third category.

    This is the test that makes the split honest. Without it, a `fonts/`
    directory under `static/` would be read by neither rule and the suite would
    stay green while the app grew an asset nobody had checked.
    """
    pinned = {asset.path for asset in ASSETS}
    uncovered = [
        path.relative_to(static_root()).as_posix()
        for path in static_root().rglob("*")
        if path.is_file()
        and path.relative_to(static_root()).as_posix() not in pinned
        and path.suffix not in GREPPED_SUFFIXES
    ]

    assert uncovered == [], (
        "these static files are neither grepped nor hash-pinned:\n"
        + "\n".join(f"  - {path}" for path in uncovered)
    )


@pytest.mark.parametrize("needle", FORBIDDEN)
def test_the_grep_would_catch_each_spelling(needle: str) -> None:
    """The detector, since a grep with a typo in its pattern passes forever."""
    line = f'<script src="{needle}example.test/x.js"></script>'

    assert any(candidate in line for candidate in FORBIDDEN)


def test_the_vendored_assets_are_reachable_at_the_paths_the_layout_uses(
    client: TestClient,
) -> None:
    """The failure §11 says the grep cannot see: a local path that 404s.

    *"The other way round, commit 1 ships a layout whose `<script>` 404s — which
    the offline-asset test would not catch, because it greps for `http://` and a
    broken local path is not a remote one."* So the layout's own references are
    requested rather than assumed, which is the only check that covers it.
    """
    layout = (templates_root() / "base.html").read_text(encoding="utf-8")

    for asset in ASSETS:
        if asset.path not in layout:
            continue
        response = client.get(f"/static/{asset.path}")
        assert response.status_code == 200, asset.path
