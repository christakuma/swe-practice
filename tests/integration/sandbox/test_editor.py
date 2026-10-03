"""The real editor launcher, against a real process on both platforms.

**The stand-in editor is this interpreter**, which is the only "editor" that is
installed on every machine CI runs on and is spelled the same way on both: a
`python -c` that writes a marker file beside the path it was handed. That makes
the launch observable without a GUI, and it exercises the thing the adapter
actually does — resolve a program, append the path, start it detached.

**Nothing is waited for by the adapter, so the test waits.** `reveal` returns as
soon as the process is started, by design: an editor outlives the request that
opened it. So every assertion about what the process *did* polls for the marker
rather than assuming it has appeared, and a poll that times out is the failure.

The Windows case has its own test, because it is the one that was wrong first: a
bare program name fails there, since `CreateProcess` searches `PATH` but does
not apply `PATHEXT`, and the file `code` installs is `code.CMD`.
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from typing import TYPE_CHECKING, Final, Protocol

import pytest

from practice.adapters.sandbox.editor import (
    DEFAULT_EDITOR,
    EDITOR_ENV,
    SubprocessEditorLauncher,
    editor_argv,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


class Launch(Protocol):
    """The fixture below, as a type: a launcher factory that cleans up."""

    def __call__(
        self, command: str, *, path: str | None = None
    ) -> SubprocessEditorLauncher: ...


#: How long a started process gets to write its marker. Generous: a cold
#: interpreter start on a loaded CI box is not fast, and a flaky integration
#: test is worse than a slow one.
_PATIENCE_SECONDS: Final = 20.0

#: An "editor" that records the file it was asked to open. `-I` for the same
#: reason the kata runner uses it: no user site-packages and no `PYTHON*`
#: variables, so a stray `sitecustomize` on the developer's machine cannot
#: change what this writes.
#:
#: Single-quoted inside, which is not cosmetic: the whole thing is passed as one
#: double-quoted `-c` argument, and a double quote in the middle of it closes
#: that quote in `shlex`'s eyes and splits the code in half. Found by running
#: it -- the process started, wrote nothing, and said nothing about why.
_MARKER_WRITER: Final = (
    "import pathlib, sys; "
    "target = pathlib.Path(sys.argv[1]); "
    "target.with_suffix('.opened').write_text(str(target), encoding='utf-8')"
)


def _wait_for(marker: Path) -> str:
    """The marker's contents, or fail saying it never appeared."""
    deadline = time.monotonic() + _PATIENCE_SECONDS
    while time.monotonic() < deadline:
        if marker.is_file():
            return marker.read_text(encoding="utf-8")
        time.sleep(0.05)
    pytest.fail(f"{marker} was never written; the editor was not started")


@pytest.fixture
def target(tmp_path: Path) -> Path:
    """A file to be revealed, with a space in its directory name.

    The space is not decoration. The path is appended as its own argv element
    rather than interpolated into a command string, and a path under
    `C:\\Program Files` is exactly what would break if that ever changed.
    """
    directory = tmp_path / "my workspace" / "repo"
    directory.mkdir(parents=True)
    found = directory / "stub.py"
    found.write_text("def two_sum():\n    ...\n", encoding="utf-8")
    return found


@pytest.fixture
def launch() -> Iterator[Launch]:
    """Build launchers, and wait for whatever they started before finishing.

    **The waiting is what this fixture is for.** The adapter deliberately does
    not wait — an editor outlives the request that opened it — and a `Popen`
    that is collected while its child still runs emits a `ResourceWarning` from
    `Popen.__del__`, which `filterwarnings = ["error"]` turns into a failure.
    That warning is right about production (a server holds its launcher for its
    whole life, so the live children are never collected) and wrong about a test
    (whose launcher dies at the end of the function, taking the list with it).

    So the test waits, which it can: its stand-in editor writes a file and
    exits, unlike the thing the adapter is built for. It reaches into
    `_started` to do it, which is what that list is -- the processes the adapter
    is holding so they are not abandoned.

    The environment is handed in rather than monkeypatched, which is what makes
    these tests honest: the real adapter captures `os.environ` once at
    construction, so a test that patched the variable afterwards would be
    testing something the adapter does not do.
    """
    built: list[SubprocessEditorLauncher] = []

    def build(command: str, *, path: str | None = None) -> SubprocessEditorLauncher:
        launcher = SubprocessEditorLauncher(
            {
                EDITOR_ENV: command,
                "PATH": path if path is not None else os.environ["PATH"],
            }
        )
        built.append(launcher)
        return launcher

    yield build

    for launcher in built:
        for process in launcher._started:
            process.wait(timeout=_PATIENCE_SECONDS)


def test_it_starts_the_configured_editor_on_the_file(
    launch: Launch, target: Path
) -> None:
    launcher = launch(f'"{sys.executable}" -I -c "{_MARKER_WRITER}"')

    assert launcher.reveal(target) is None
    assert _wait_for(target.with_suffix(".opened")) == str(target)


def test_it_returns_a_problem_when_the_editor_is_not_installed(
    launch: Launch, target: Path
) -> None:
    """The branch the whole three-field DTO exists for. The sentence names the
    variable, because every way this fails has the same fix.
    """
    problem = launch("definitely-not-an-editor-xyz").reveal(target)

    assert problem is not None
    assert EDITOR_ENV in problem
    assert "definitely-not-an-editor-xyz" in problem


def test_it_returns_a_problem_when_the_editor_cannot_be_started(
    launch: Launch, tmp_path: Path, target: Path
) -> None:
    """Resolved, and still not startable.

    Every `OSError` is caught and not only `FileNotFoundError`, and this is the
    case that distinguishes them: a file the resolver is happy with -- named
    `.exe` on Windows, with the execute bit on POSIX -- whose contents are not a
    program. Windows answers `WinError 193`, POSIX `Errno 8`, and the solver
    gets the same sentence either way.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    stem = "practice-editor-probe"
    program = bin_dir / (f"{stem}.exe" if os.name == "nt" else stem)
    program.write_bytes(b"this is not a program\n")
    program.chmod(0o755)
    if shutil.which(stem, path=str(bin_dir)) is None:  # pragma: no cover
        pytest.skip(f"{program.name} is not resolvable on this platform")

    problem = launch(stem, path=str(bin_dir)).reveal(target)

    assert problem is not None
    assert "could not be started" in problem


@pytest.mark.skipif(os.name != "nt", reason="PATHEXT is a Windows mechanism")
def test_a_windows_editor_is_found_through_pathext(
    launch: Launch, tmp_path: Path, target: Path
) -> None:
    """The papercut this adapter exists to absorb, pinned.

    `Popen(["code", path])` raises `FileNotFoundError [WinError 2]` on Windows,
    because `CreateProcess` searches `PATH` and does not apply `PATHEXT` -- and
    the file VS Code installs is `code.CMD`. So the program is resolved before
    it is started, and a `.cmd` on `PATH` under a bare name has to work.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    marker = tmp_path / "opened.txt"
    (bin_dir / "practiceedit.cmd").write_text(
        f'@echo off\r\necho %1 > "{marker}"\r\n', encoding="utf-8"
    )

    launcher = launch("practiceedit", path=str(bin_dir))

    assert launcher.reveal(target) is None
    assert str(target) in _wait_for(marker)


class TestTheConfiguredCommand:
    """`editor_argv`: one variable, split the way a shell would split it."""

    def test_it_defaults_to_code_when_nothing_is_configured(self) -> None:
        assert editor_argv({}) == (DEFAULT_EDITOR,)

    def test_an_empty_variable_is_not_an_empty_command(self) -> None:
        """An exported-but-unset variable is the likeliest way to get one, and
        "no editor configured" is not what it means.
        """
        assert editor_argv({EDITOR_ENV: "   "}) == (DEFAULT_EDITOR,)

    def test_it_splits_arguments_off_the_command(self) -> None:
        assert editor_argv({EDITOR_ENV: "code -g --wait"}) == (
            "code",
            "-g",
            "--wait",
        )

    @pytest.mark.skipif(os.name != "nt", reason="backslashes are only escapes on POSIX")
    def test_a_windows_path_keeps_its_backslashes(self) -> None:
        """`shlex.split` in POSIX mode eats them, which would turn
        `C:\\Tools\\npp.exe` into `C:Toolsnpp.exe` and resolve to nothing.
        """
        argv = editor_argv({EDITOR_ENV: r"C:\Tools\npp.exe -multiInst"})

        assert argv == (r"C:\Tools\npp.exe", "-multiInst")

    @pytest.mark.skipif(os.name != "nt", reason="non-POSIX mode is the Windows path")
    def test_a_quoted_windows_path_loses_only_its_quotes(self) -> None:
        """Non-POSIX `shlex` keeps the quotes in the token, which made the first
        run of this adapter look for a program literally called `"C:\\...exe"`.
        An editor under `C:\\Program Files` is the case that needs them.
        """
        argv = editor_argv({EDITOR_ENV: r'"C:\Program Files\Ed\ed.exe" --new'})

        assert argv == (r"C:\Program Files\Ed\ed.exe", "--new")

    def test_the_environment_is_read_once_at_construction(
        self, monkeypatch: pytest.MonkeyPatch, target: Path
    ) -> None:
        """A running server must not have its editor changed underneath it half
        way through a session, which is why the adapter copies the environment.
        """
        monkeypatch.setenv(EDITOR_ENV, "definitely-not-an-editor-xyz")
        launcher = SubprocessEditorLauncher()
        monkeypatch.setenv(EDITOR_ENV, "also-not-an-editor-abc")

        problem = launcher.reveal(target)

        assert problem is not None
        assert "definitely-not-an-editor-xyz" in problem


@pytest.fixture(autouse=True)
def _no_real_editor(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nothing in this file may open the developer's actual editor.

    Every test here configures its own command, so this is belt and braces
    against a future one that forgets: an integration suite that opened VS Code
    four times is an integration suite nobody runs twice.
    """
    monkeypatch.delenv(EDITOR_ENV, raising=False)
