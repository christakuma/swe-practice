"""`practice serve` — the command that boots the other adapter.

Here rather than in `tests/integration/` with the other CLI tests, because what
is being tested is the web surface's startup rule and not the CLI's argument
handling: §8.3's first guard is *"startup asserts the host is 127.0.0.1, with a
test that fails if a future change binds 0.0.0.0."* This is that test.

`uvicorn.run` is replaced rather than called. A test that actually started a
server would bind a port, which is a flaky test on a developer's machine and a
slow one everywhere; what has to be proved is which host it was *asked* to bind,
and that is an argument.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
import uvicorn
from typer.testing import CliRunner

from practice.interface.cli.main import DEFAULT_HOST, DEFAULT_PORT, app

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


class Recorder:
    """Stands in for `uvicorn.run` and remembers what it was handed."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, served: object, **kwargs: Any) -> None:
        self.calls.append({"app": served, **kwargs})


@pytest.fixture
def uvicorn_run(monkeypatch: pytest.MonkeyPatch) -> Recorder:
    recorder = Recorder()
    # Patched on the module rather than on the CLI's reference to it: `serve`
    # calls `uvicorn.run(...)`, which is an attribute lookup at call time, so one
    # substitution covers it without the test having to know how it was imported.
    monkeypatch.setattr(uvicorn, "run", recorder)
    return recorder


def test_it_binds_loopback_by_default(
    uvicorn_run: Recorder, tmp_path: Path, library: Path
) -> None:
    result = runner.invoke(
        app,
        [
            "serve",
            "--content-root",
            str(library),
            "--workspace-root",
            str(tmp_path / "ws"),
            "--database",
            str(tmp_path / "practice.db"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert uvicorn_run.calls[0]["host"] == DEFAULT_HOST
    assert uvicorn_run.calls[0]["port"] == DEFAULT_PORT
    assert f"http://{DEFAULT_HOST}:{DEFAULT_PORT}" in result.output


# The literal this guard exists to refuse, so bandit's S104 is the rule firing on
# the test for the rule.
@pytest.mark.parametrize(
    "host",
    ["0.0.0.0", "192.168.1.14", "practice.example"],  # noqa: S104
)
def test_it_refuses_to_bind_anywhere_else(
    uvicorn_run: Recorder, library: Path, host: str
) -> None:
    """The criterion itself: a future change to `0.0.0.0` fails here.

    Exit 2 rather than 1, matching every other "this invocation cannot be
    satisfied" in the CLI — the command did not run and produced no verdict.
    """
    result = runner.invoke(
        app, ["serve", "--host", host, "--content-root", str(library)]
    )

    assert result.exit_code == 2
    assert "refusing to bind" in result.output
    assert uvicorn_run.calls == []


def test_it_says_the_app_is_offline(
    uvicorn_run: Recorder, tmp_path: Path, library: Path
) -> None:
    """Printed because it is the one thing about this server worth knowing.

    A local web app that opens a browser tab looks exactly like one that is
    talking to a server, and the claim of PLAN.md §8.2 is that it is not.
    """
    result = runner.invoke(
        app,
        [
            "serve",
            "--content-root",
            str(library),
            "--workspace-root",
            str(tmp_path / "ws"),
            "--database",
            str(tmp_path / "practice.db"),
        ],
    )

    assert "Offline" in result.output
    assert len(uvicorn_run.calls) == 1


def test_building_the_app_reads_no_database(
    uvicorn_run: Recorder, tmp_path: Path, library: Path
) -> None:
    """Starting the server must not create a database on a fresh machine.

    `test_building_the_graph_writes_nothing_to_disk` makes this claim about
    `build_services`; this is the same claim about the command that calls it, which
    is the one a user runs. A route creates the file on the first attempt.
    """
    database = tmp_path / "data" / "practice.db"

    runner.invoke(
        app,
        [
            "serve",
            "--content-root",
            str(library),
            "--workspace-root",
            str(tmp_path / "ws"),
            "--database",
            str(database),
        ],
    )

    assert not database.exists()
    assert len(uvicorn_run.calls) == 1


@pytest.fixture
def library(tmp_path: Path) -> Path:
    """An empty content root, so nothing here depends on the real library."""
    root = tmp_path / "content"
    root.mkdir()
    return root
