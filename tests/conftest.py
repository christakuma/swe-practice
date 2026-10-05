"""Shared pytest configuration.

Five things, and they are here rather than anywhere else for the same reason: a
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

**No test inherits the developer's scheduler choice.** `PRACTICE_SCHEDULER`
(Phase 13) is an environment variable a user is meant to set in their shell
profile, and `build_services()` reads it — so a developer running the suite with
`fsrs` exported would be running a different wiring than CI, and the tests that
assert on the default would fail on their machine and nowhere else. Cleared for
the same reason the database is redirected: the suite must not depend on the
state of the machine it happens to be on. A test that wants a specific scheduler
passes it to `build_services`, which is what that override is for.

**No test opens a browser**, and this one was found by the suite doing it. `up`
calls `open_in_browser` once its preflight passes, and the browser stub in
`tests/integration/test_cli_up.py` is a fixture a test has to *request* — so
`test_the_report_names_the_scheduler_that_will_move_your_cards`, which takes
`served` and asserts `code == 0`, opened a real tab at `127.0.0.1:8765` on every
run of the full suite. With `uvicorn.run` stubbed there is nothing listening, so
what it put in front of whoever was running the tests was a browser window
stealing focus and then failing to connect. Exactly the shape the database rule
above has: remembered per test, and one test did not.

**Hypothesis runs without a deadline.** Its default fails an example that takes
over 200ms, which is a useful guard against an accidentally quadratic property and
a bad fit for this suite: the scheduler properties are microseconds of arithmetic,
so the only thing the deadline can catch here is a CI runner pausing — a flake with
no defect behind it, in the suite that is meant to be the most trustworthy. The
bound that matters, `max_examples`, is left alone.
"""

from __future__ import annotations

import webbrowser
from itertools import count
from typing import TYPE_CHECKING

import pytest
from hypothesis import settings

from practice.config import DATABASE_PATH_ENV, SCHEDULER_ENV

settings.register_profile("practice", deadline=None)
settings.load_profile("practice")

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

    It also clears `PRACTICE_SCHEDULER`, which is not a database and is here for
    exactly the reason this fixture is autouse: it is a rule about not inheriting
    the machine's state, and a rule remembered per test is one a test will
    forget.
    """
    base = tmp_path_factory.getbasetemp() / "db" / str(next(_databases))
    monkeypatch.setenv(DATABASE_PATH_ENV, str(base / "practice.db"))
    # Not a database, but the same rule and the same fixture: see the module
    # docstring. `raising=False` because the usual case is that it is unset.
    monkeypatch.delenv(SCHEDULER_ENV, raising=False)


@pytest.fixture(autouse=True)
def _no_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop any test from opening a real browser window. See the module docstring.

    Answers `True`, which is `webbrowser.open`'s "a handler took it" — so the
    default makes `open_in_browser` return `None` and the command under test
    takes its success path. A test that wants a decline, a `webbrowser.Error` or
    a record of the calls patches the attribute itself; this fixture is autouse
    and therefore set up first, so the test's own patch wins for the test that
    asked for one.
    """
    monkeypatch.setattr(webbrowser, "open", lambda *_args, **_kwargs: True)


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
