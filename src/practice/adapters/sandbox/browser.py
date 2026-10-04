"""Opening the solver's browser on the URL the launcher just bound.

**Why this is beside `editor.py` rather than in the CLI that calls it.** Both do
the same thing — hand something on the solver's own machine to a program the
solver chose, detached, and expect it to outlive the call. `editor.py`'s
docstring argues that the one package allowed to start a process should stay
one package, because a rule enforced at one import is a rule; this is the second
case of it, and splitting the two would mean a reader comparing them had to look
in two layers. `webbrowser` reaches a process by a different route — `os.startfile`
on Windows, a `Popen` of the registered opener elsewhere — so
`test_only_the_sandbox_starts_a_process` would not have caught it being put
anywhere else. That is a reason to be deliberate about it, not a licence.

**It returns a sentence rather than raising, like `EditorLauncher.reveal`.** Not
opening a browser is not a reason to refuse to serve: the URL is already printed
and a solver who runs this over SSH, in WSL, or on a machine with no registered
handler is better served by "open it yourself" than by an exit code. Every way
this fails ends in the same instruction, which is why there is one sentence for
all of them.

**Two failure signals, and `webbrowser` uses a different mechanism for each.**
`open` returns `False` when it found a handler and the handler declined, and
raises `webbrowser.Error` when no handler is registered at all — so a caller
that only checked the return value would get a traceback on the headless case,
which is the case most likely to happen. Both end up as the same sentence.

There is a third outcome this cannot detect: on a POSIX box with no display,
`webbrowser` may start a *text* browser and take over the terminal the server
is about to print to. Nothing here can tell that apart from success, which is
why `practice up --no-open` exists rather than a guess about `$DISPLAY`.
"""

from __future__ import annotations

import webbrowser
from typing import Final

__all__ = ["open_in_browser"]

#: `webbrowser`'s own code for "open in a new tab, and raise the window". A
#: constant because the integer is meaningless at the call site: `new=2` reads
#: as a magic number and this reads as the intent.
_NEW_TAB: Final = 2


def open_in_browser(url: str) -> str | None:
    """Open `url`, and return why it could not be opened if it could not.

    `webbrowser.open` is looked up on the module at call time rather than bound
    as a default argument, so one `monkeypatch.setattr(webbrowser, "open", ...)`
    covers every caller — the same seam `tests/web/test_serve.py` uses for
    `uvicorn.run`, and the reason neither needs an injected port.
    """
    try:
        opened = webbrowser.open(url, new=_NEW_TAB)
    except webbrowser.Error:
        # No handler registered at all: a container, a bare server, WSL without
        # `wslu`. Not an error worth a stack trace — the URL is on screen.
        opened = False
    if opened:
        return None
    return f"no browser could be opened for you; visit {url} yourself"
