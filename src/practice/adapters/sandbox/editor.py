"""Launching the solver's own editor on a file in the workspace.

Satisfies `practice.domain.ports.EditorLauncher` structurally, like every
adapter here (ADR 0002).

**Why this lives under `adapters/sandbox/` even though nothing about it is
sandboxed.** `tests/unit/test_architecture.py` enforces that exactly one package
starts a process, because the trust split in PLAN.md §8.1 is only a split if
there is a single place that does it. This is the one process start in the
project that is deliberately *not* sandboxed: no scoped environment, no output
capture, no timeout, no process-tree kill. It is a GUI program on the solver's
own machine, started on their explicit click, and it is expected to outlive the
request that started it. Putting it anywhere else would mean relaxing the
architecture rule to two packages, which is exactly the erosion that test
exists to prevent — so it goes here, next to the two starts that *are* scoped,
where a reader comparing the three can see which is which.

**One environment variable, and `$EDITOR` is deliberately not consulted.**
`$EDITOR` and `$VISUAL` name a program that expects to own a terminal, and this
launch has none: `PRACTICE_EDITOR=vim` would succeed in `Popen`, draw nothing
anywhere, and report success — the worst available outcome, because the solver
would be told their editor was opened and then sit looking at a browser tab. So
there is one variable with one meaning, and the default is `code`.

**Fire-and-forget still has to collect its litter, and the test suite is what
found it.** A `Popen` nobody waits for emits a `ResourceWarning` from
`Popen.__del__` the moment it is garbage collected — "subprocess is still
running" — which this project's `filterwarnings = ["error"]` turns into a
failing test, correctly: abandoning a child without waiting also leaves a zombie
on POSIX, because nothing ever reaps it. So the launcher keeps a reference to
every process it has started and polls them on the way past, which reaps the
ones that have exited and keeps the live ones from being collected. The list
holds one entry per editor window still open, which on a single-user local tool
is a number in the low single digits.

**A bare program name does not work on Windows, and this is the papercut the
module exists to absorb.** Proven by running it rather than reasoned about:
`Popen(["code", path])` raises `FileNotFoundError [WinError 2]`, because
`CreateProcess` searches `PATH` but does not apply `PATHEXT`, and the file that
is actually installed is `code.CMD`. `shutil.which` does apply it, and `Popen`
of the resolved `.CMD` path then works. So the program is resolved before it is
started — through `resolve_program`, which is the one function in this package
that already knows this, and whose docstring records the same finding from the
other direction.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import threading
from typing import TYPE_CHECKING, Final

from practice.adapters.sandbox.execution import resolve_program

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

__all__ = [
    "DEFAULT_EDITOR",
    "EDITOR_ENV",
    "SubprocessEditorLauncher",
    "editor_argv",
]

#: The one variable that decides which editor is opened. Named for this app
#: rather than reusing `$EDITOR`: see the module docstring.
EDITOR_ENV: Final = "PRACTICE_EDITOR"

#: What is tried when nothing is configured. A guess, and the docstring of
#: `reveal`'s refusal names the variable that corrects it.
DEFAULT_EDITOR: Final = "code"


def editor_argv(environment: Mapping[str, str] | None = None) -> tuple[str, ...]:
    """The configured editor command, split the way a shell would split it.

    `shlex.split` so `PRACTICE_EDITOR="code -g"` works. The split is for the
    *author* of the variable's convenience; nothing here reaches a shell, and
    the file path is appended as its own argv element rather than interpolated
    into a string.

    **`posix=False` on Windows, and then the quotes are stripped by hand.** In
    POSIX mode `shlex` treats a backslash as an escape, which turns
    `C:\\Tools\\npp.exe` into `C:Toolsnpp.exe` and resolves to nothing. In
    non-POSIX mode it splits on quotes correctly and *keeps them in the token* --
    documented behaviour, and it produced a program name of `'"C:\\...\\python.exe"'`
    the first time this ran. Stripping one matching pair is the whole fix, and it
    is the case that matters: an editor under `C:\\Program Files`, which is where
    editors are.

    An empty or whitespace-only variable falls back to the default rather than
    producing an empty argv, because an exported-but-unset variable is the most
    likely way to get one and "no editor configured" is not what it means.
    """
    source = environment if environment is not None else os.environ
    configured = source.get(EDITOR_ENV, "").strip()
    if not configured:
        return (DEFAULT_EDITOR,)
    if os.name != "nt":
        parts = shlex.split(configured)
    else:
        parts = [_unquoted(part) for part in shlex.split(configured, posix=False)]
    return tuple(parts) if parts else (DEFAULT_EDITOR,)


def _unquoted(part: str) -> str:
    """One matching pair of surrounding quotes removed. See `editor_argv`."""
    for quote in ('"', "'"):
        if len(part) > 1 and part.startswith(quote) and part.endswith(quote):
            return part[1:-1]
    return part


class SubprocessEditorLauncher:
    """Satisfies `practice.domain.ports.EditorLauncher` with one detached process.

    Holds no state about any one attempt — the path is an argument — so the
    composition root builds exactly one, like the pytest runner.
    """

    __slots__ = ("_environment", "_lock", "_started")

    def __init__(self, environment: Mapping[str, str] | None = None) -> None:
        # Captured rather than read per call, so a test can hand this a
        # dictionary and a running server cannot have its editor changed
        # underneath it half way through a session.
        self._environment = dict(environment if environment is not None else os.environ)
        #: Processes started and not yet known to have exited. See the module
        #: docstring: holding them is what stops `Popen.__del__` complaining
        #: about a child nobody waited for, and polling them is what reaps it.
        self._started: list[subprocess.Popen[bytes]] = []
        #: The server calls `reveal` from a threadpool, so two reveals can land
        #: at once. One lock over the list, held for the length of a `poll`.
        self._lock = threading.Lock()

    def reveal(self, path: Path) -> str | None:
        """Open `path`, and return why it could not be opened if it could not.

        **Nothing is waited for and nothing is captured.** An editor is expected
        to outlive this request: waiting would hang the endpoint for as long as
        the solver has the window open, and a terminal editor inheriting the
        server's streams would fight the server for them. All three are
        `DEVNULL`, which also means a program that decides to prompt gets EOF
        and exits rather than blocking forever.

        The returned sentence names the variable, because every way this fails
        is the same fix — the default `code` is a guess, and the solver's editor
        may be something else entirely.
        """
        argv = editor_argv(self._environment)
        program = resolve_program(argv[0], self._environment)
        if program is None:
            return (
                f"{argv[0]!r} is not on this machine's PATH, so the file was not "
                f"opened for you; set {EDITOR_ENV} to the command that starts "
                f"your editor, or open the path above yourself"
            )
        return self._start((str(program), *argv[1:], str(path)), argv[0])

    def _start(self, argv: Sequence[str], program: str) -> str | None:
        try:
            # Not a context manager: `with Popen(...)` waits for the process on
            # the way out, which is the one thing this must not do.
            process = subprocess.Popen(  # noqa: S603  (argv list, no shell)
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except OSError as exc:
            # Every `OSError`, not just `FileNotFoundError`: a resolved path can
            # still be a directory, a file with no execute bit, or an
            # architecture this machine cannot run, and all three arrive here.
            return (
                f"{program} was found but could not be started ({exc}); open the "
                f"path above yourself, or set {EDITOR_ENV} to something else"
            )
        self._keep(process)
        return None

    def _keep(self, process: subprocess.Popen[bytes]) -> None:
        """Hold the new process and let go of the ones that have finished.

        `poll` is what reaps an exited child; without it a POSIX server would
        accumulate a zombie per editor it ever opened. Holding the live ones is
        what keeps `Popen.__del__` quiet — see the module docstring.
        """
        with self._lock:
            self._started = [
                running
                for running in (*self._started, process)
                if running.poll() is None
            ]
