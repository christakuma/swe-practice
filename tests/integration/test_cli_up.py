"""`practice up` — the front door, and the four questions it asks first.

Integration tests because the whole point of this command is the filesystem: it
creates a workspace directory, migrates a real SQLite file and lists a real
content root, and a suite that faked any of those would be testing the report
rather than the setup.

Two seams are substituted and nothing else. `uvicorn.run`, for the reason
`tests/web/test_serve.py` gives — a test that bound a port would be flaky on a
developer's machine — and `webbrowser.open`, because a test suite that opened
fifty browser tabs is its own punishment. Both are patched on their own module,
so neither test has to know how the CLI imported them.

**The claim the exit criterion rests on is `test_a_clean_machine_is_set_up_in_one
_command`**: an empty data directory, no database, no workspace root, one
invocation, and the app is serving. Everything else here is a refusal, because
refusals are where this command earns its keep — a server that boots without git
is a tool that looks fine until the moment the solver has done the work.
"""

from __future__ import annotations

import webbrowser
from importlib.metadata import version
from typing import TYPE_CHECKING, Any

import pytest
import uvicorn
from typer.testing import CliRunner

from practice.adapters.persistence.sqlite import Database, Migration, load_migrations
from practice.adapters.sandbox.env import ToolNotFoundError
from practice.interface.cli import launcher
from practice.interface.cli.launcher import prepare
from practice.interface.cli.main import DEFAULT_HOST, DEFAULT_PORT, app
from tests.integration.conftest import a_kata, a_scenario

if TYPE_CHECKING:
    from pathlib import Path

    from tests.integration.conftest import WriteExercise

runner = CliRunner()


class Recorder:
    """Stands in for a one-call function and remembers what it was handed."""

    def __init__(self, answer: Any = None) -> None:
        self.answer = answer
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append((args, kwargs))
        return self.answer


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch) -> Recorder:
    recorder = Recorder()
    monkeypatch.setattr(uvicorn, "run", recorder)
    return recorder


@pytest.fixture
def opened(monkeypatch: pytest.MonkeyPatch) -> Recorder:
    recorder = Recorder(answer=True)
    monkeypatch.setattr(webbrowser, "open", recorder)
    return recorder


@pytest.fixture
def stocked(write_exercise: WriteExercise) -> None:
    """One kata and one git scenario, so the library step has both kinds."""
    write_exercise(a_scenario())
    write_exercise(a_kata())


def run(library: Path, tmp_path: Path, *arguments: str) -> tuple[int, str]:
    """`up` with all three paths passed explicitly, as the CLI tests do."""
    result = runner.invoke(
        app,
        [
            "up",
            *arguments,
            "--content-root",
            str(library),
            "--workspace-root",
            str(tmp_path / "cache" / "ws"),
            "--database",
            str(tmp_path / "data" / "practice.db"),
        ],
    )
    return result.exit_code, result.output


# --- the exit criterion ----------------------------------------------------


@pytest.mark.usefixtures("stocked")
def test_a_clean_machine_is_set_up_in_one_command(
    served: Recorder, opened: Recorder, library: Path, tmp_path: Path
) -> None:
    """Phase 12's exit criterion, as narrowly as it can be stated.

    Neither directory exists when this starts. One invocation has to end with a
    migrated database, a workspace root, a browser pointed at the app and a
    server running — which is the whole of "clone it and be practising", minus
    the clone.
    """
    database = tmp_path / "data" / "practice.db"
    workspaces = tmp_path / "cache" / "ws"
    assert not database.exists()
    assert not workspaces.exists()

    code, output = run(library, tmp_path)

    assert code == 0, output
    assert database.is_file()
    assert workspaces.is_dir()
    assert served.calls[0][1]["host"] == DEFAULT_HOST
    assert served.calls[0][1]["port"] == DEFAULT_PORT
    assert opened.calls == [((f"http://{DEFAULT_HOST}:{DEFAULT_PORT}",), {"new": 2})]


@pytest.mark.usefixtures("stocked", "served", "opened")
def test_it_says_so_on_the_run_that_creates_the_history(
    library: Path, tmp_path: Path
) -> None:
    """Once, and only once.

    The database is the one piece of state here that cannot be regenerated
    (`config.py`), so where it landed is worth a sentence on the run that put it
    there — and is noise on every run after.
    """
    first = run(library, tmp_path)[1]
    second = run(library, tmp_path)[1]

    assert "First run" in first
    assert "First run" not in second


@pytest.mark.usefixtures("stocked", "served", "opened")
def test_it_reports_what_it_found_and_not_just_that_it_was_fine(
    library: Path, tmp_path: Path
) -> None:
    """Which git, which library, how many exercises, where the database is.

    A report of four `ok`s and no detail cannot tell a solver that
    `PRACTICE_CONTENT_ROOT` is still pointing at last week's checkout, which is
    the thing a first-run report is for.
    """
    output = run(library, tmp_path)[1]

    assert "2 exercises" in output
    assert "1 git scenario" in output
    assert "1 kata" in output
    assert str(library) in output


@pytest.mark.usefixtures("stocked", "opened")
def test_it_still_says_the_app_is_offline(
    served: Recorder, library: Path, tmp_path: Path
) -> None:
    """A command that opens a browser tab has more need of this line, not less.

    `serve` prints it because a local web app looks exactly like one talking to a
    server; `up` opens the tab for you, so it is the command where the question
    actually occurs to someone.
    """
    output = run(library, tmp_path)[1]

    assert "Offline" in output
    assert len(served.calls) == 1


# --- refusals --------------------------------------------------------------


@pytest.mark.usefixtures("stocked")
def test_it_refuses_an_empty_library(
    served: Recorder, opened: Recorder, tmp_path: Path
) -> None:
    """An empty content root is a server with nothing to offer.

    The `stocked` library is deliberately *not* used here: the root passed is a
    different, empty directory, which is what a stale
    `PRACTICE_CONTENT_ROOT` or a `pip install` with no `content/` beside it
    looks like.
    """
    empty = tmp_path / "elsewhere"
    empty.mkdir()

    code, output = run(empty, tmp_path)

    assert code == 2
    assert "no exercises" in output
    assert served.calls == []
    assert opened.calls == []


def test_it_refuses_a_library_one_exercise_cannot_be_loaded_from(
    served: Recorder,
    opened: Recorder,
    write_exercise: WriteExercise,
    library: Path,
    tmp_path: Path,
) -> None:
    """One bad file is not a smaller library, it is a browse page that 500s.

    `FilesystemContentRepository` fails the whole listing on purpose, so that an
    exercise cannot vanish quietly. This is the command that turns that into an
    instruction instead of a traceback.
    """
    write_exercise({"id": "git/broken"}, raw="kind: git_scenario\nid: [", notes=None)

    code, output = run(library, tmp_path)

    assert code == 2
    assert "practice validate" in output
    assert served.calls == []
    assert opened.calls == []


@pytest.mark.usefixtures("stocked")
def test_it_refuses_when_git_is_not_installed(
    served: Recorder,
    opened: Recorder,
    monkeypatch: pytest.MonkeyPatch,
    library: Path,
    tmp_path: Path,
) -> None:
    """The headline case, and the one this command exists for.

    With no git there is no fixture, no attempt and no grading, so every other
    step is beside the point. Without this check the news arrives as a 500 on the
    first scenario the solver opens, twenty minutes after they installed the
    tool and with nothing in it that says `install git`.
    """

    def missing() -> None:
        raise ToolNotFoundError("git is not on PATH. install git 2.32 or newer.")

    monkeypatch.setattr(launcher, "find_git", missing)

    code, output = run(library, tmp_path)

    assert code == 2
    assert "install git" in output
    assert served.calls == []
    assert opened.calls == []


@pytest.mark.usefixtures("stocked")
def test_it_reports_every_blocker_rather_than_the_first(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Two problems, one run.

    A chain that stopped at the first failure would make a stranger run this
    three times to learn three facts, and a machine with no git plausibly has no
    writable data directory either.
    """

    def missing() -> None:
        raise ToolNotFoundError("git is not on PATH.")

    monkeypatch.setattr(launcher, "find_git", missing)
    empty = tmp_path / "elsewhere"
    empty.mkdir()

    code, output = run(empty, tmp_path)

    assert code == 2
    assert "git is not on PATH" in output
    assert "no exercises" in output


@pytest.mark.usefixtures("stocked")
# The literal the guard refuses, so bandit's S104 fires on the test for the rule.
@pytest.mark.parametrize("host", ["0.0.0.0", "10.0.0.4"])  # noqa: S104
def test_it_inherits_the_loopback_guard(
    served: Recorder,
    opened: Recorder,
    library: Path,
    tmp_path: Path,
    host: str,
) -> None:
    """§8.3's first guard, through the shared `_bound`.

    Checked *before* anything is created, which is the part worth asserting: a
    command that migrated a database and then refused to bind would have done
    work on behalf of an invocation it was never going to honour.
    """
    code, output = run(library, tmp_path, "--host", host)

    assert code == 2
    assert "refusing to bind" in output
    assert not (tmp_path / "data").exists()
    assert served.calls == []
    assert opened.calls == []


# --- the pieces ------------------------------------------------------------


@pytest.mark.usefixtures("stocked")
def test_no_browser_is_opened_when_none_was_asked_for(
    served: Recorder, opened: Recorder, library: Path, tmp_path: Path
) -> None:
    """`--no-open`, for a headless box — and it still serves.

    The flag exists because of the one outcome `open_in_browser` cannot detect:
    on a POSIX machine with no display, `webbrowser` may start a *text* browser
    and take the terminal the server is about to print to.
    """
    code, _ = run(library, tmp_path, "--no-open")

    assert code == 0
    assert opened.calls == []
    assert len(served.calls) == 1


@pytest.mark.usefixtures("stocked")
def test_a_browser_that_will_not_open_does_not_stop_the_server(
    served: Recorder, monkeypatch: pytest.MonkeyPatch, library: Path, tmp_path: Path
) -> None:
    """The URL is already on screen, so there is nothing left to refuse over."""
    monkeypatch.setattr(webbrowser, "open", Recorder(answer=False))

    code, output = run(library, tmp_path)

    assert code == 0
    assert "visit" in output
    assert len(served.calls) == 1


def test_a_database_written_by_a_newer_practice_is_refused_not_opened(
    served: Recorder, opened: Recorder, library: Path, tmp_path: Path
) -> None:
    """A `MigrationError` is a sentence here and a 500 if it waits.

    Built through `Database`'s injectable migration list — the seam that exists
    so a test can construct a history that must be refused without putting a
    broken `.sql` file in the shipped directory. The fabricated version is one
    past the last one shipped, so the next `migrate()` finds it applied and
    unknown.

    **Derived from `load_migrations()` rather than written as a literal**, which
    is what it was until Phase 13 shipped 0002 and made the literal `2` a version
    this `practice` does have. The test then passed for the wrong reason — it was
    constructing a perfectly ordinary database and asserting a refusal — which is
    the failure mode a hard-coded "version from the future" has by construction.
    """
    database = tmp_path / "data" / "practice.db"
    from_the_future = load_migrations()[-1].version + 1
    ahead = Database(
        database,
        migrations=[
            *load_migrations(),
            Migration(
                version=from_the_future,
                name="from_the_future",
                sql="CREATE TABLE c (d TEXT)",
            ),
        ],
    )
    ahead.migrate()

    code, output = run(library, tmp_path)

    assert code == 2
    assert "written by a newer one" in output
    assert served.calls == []
    assert opened.calls == []


@pytest.mark.usefixtures("stocked")
def test_prepare_reports_a_second_run_as_not_fresh(
    library: Path, tmp_path: Path
) -> None:
    """`fresh` is about the database file, not about the machine.

    Asserted on `prepare` directly rather than through the output, because the
    flag is the thing `up` branches on and a test on the sentence would pass
    just as well if the branch read the wrong field.
    """
    paths = {
        "content": library,
        "workspaces": tmp_path / "cache" / "ws",
        "database": tmp_path / "data" / "practice.db",
    }

    first = prepare(**paths)
    second = prepare(**paths)

    assert first.fresh is True
    assert second.fresh is False
    assert first.ok
    assert second.ok


def test_it_reports_the_installed_version() -> None:
    """`--version` on the app itself, not on `up`, and eager.

    Here because this file is already about the commands somebody runs *at*
    the tool rather than through it. The assertion is against the package
    metadata rather than a literal, which is the claim: there is one version
    number in this project and it is in `pyproject.toml`. A test matching
    "1.0.0" would pass on the next release and be wrong.
    """
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == f"practice {version('swe-practice')}"


@pytest.mark.usefixtures("stocked")
def test_prepare_creates_nothing_it_was_not_asked_to(
    library: Path, tmp_path: Path
) -> None:
    """Two directories and one file, and no stray parents anywhere else.

    The side effect is deliberate and bounded (`launcher.py`), and "bounded" is
    only true if it is checked: a `mkdir(parents=True)` on a path assembled
    wrongly is how a tool ends up creating `~/None`.
    """
    report = prepare(
        content=library,
        workspaces=tmp_path / "cache" / "ws",
        database=tmp_path / "data" / "practice.db",
    )

    assert report.ok
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "cache",
        "content",
        "data",
    ]
