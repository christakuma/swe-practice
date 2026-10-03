"""One kata solved in a real editor, with the verdict arriving in the browser.

The Phase 10 exit criterion: *save in VS Code, see the verdict update in the
browser.* Every adapter here is the real one — the filesystem content library,
the subprocess provisioner, a real `watchfiles` watcher, a real pytest run, a
real SQLite file, a real process started as the editor — and the only two things
standing in are the browser (the test client, which sends what
`SameOriginMiddleware` requires) and the editor itself.

**The editor is this interpreter.** `PRACTICE_EDITOR` is pointed at a `python
-c` that writes the solution into the file it is handed, which is exactly what a
solver does in VS Code and the only way to do it on every machine CI runs on.
That also makes the reveal's launch observable: if the editor were not really
started, the file would never change and nothing downstream would happen.

**The stream is driven directly, not over HTTP.** `stream` is a module-level
function for this reason: an SSE response read through the test client is a
connection the test has to tear down, and what this test is about is the loop —
save, re-grade, verdict — not HTTP's part in carrying it. `tests/web/test_watch.py`
covers the response shape, and the route is three lines over this function.

**One test, deliberately**, on §9's rule: it costs two pytest subprocesses, a
provisioned workspace and a real directory watch. What only this layer can show
is that the pieces compose — reveal, save, notice, grade, stream, submit — and
that the log at the end of it records one submission and not four saves.
"""

from __future__ import annotations

import asyncio
import sys
import time
from base64 import b64encode
from dataclasses import replace
from typing import TYPE_CHECKING, Final

import pytest
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient
from starlette.requests import Request

from practice.adapters.sandbox.editor import EDITOR_ENV
from practice.adapters.sandbox.watcher import WatchfilesFileWatcher
from practice.composition import build_services
from practice.config import content_root
from practice.domain.attempt import SolutionSaved
from practice.domain.ids import AttemptId, ExerciseId
from practice.interface.web import create_app
from practice.interface.web.app import templates_root
from practice.interface.web.routes.editor import stream

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from practice.composition import Services

TWO_SUM = "katas/two-sum"

ORIGIN = "http://127.0.0.1"
BROWSER: Final = {"origin": ORIGIN, "sec-fetch-site": "same-origin"}

#: How long the real watcher gets to notice a real save, and the grading pass
#: that follows it gets to finish. Generous on purpose: this is the one test in
#: the suite whose timing depends on the operating system's file notifications.
_PATIENCE: Final = 60.0

#: Short, so the stream's first tick -- which is how this test knows the watcher
#: is actually listening before it writes anything -- arrives promptly.
_TICK: Final = 0.2

#: What the solver types in their own editor. One pass, a dict, correct.
SOLVED = """\
def two_sum(numbers, target):
    seen = {}
    for index, value in enumerate(numbers):
        complement = target - value
        if complement in seen:
            return (seen[complement], index)
        seen[value] = index
    raise ValueError("no pair of values adds up to the target")
"""

#: The "editor": writes `SOLVED` into the file it is given, and exits.
#:
#: **Base64, and that is not paranoia.** The whole script is passed as one
#: double-quoted `-c` argument, and `SOLVED` contains a double quote of its own
#: (`ValueError("no pair ...")`) -- which closes that quote and splits the code
#: in half. The first version of this test did exactly that: the process
#: started, the launch reported success, the file never changed, and the only
#: symptom was a sixty-second timeout in the watcher. Base64 has no quotes in
#: it, and `write_bytes` keeps the LF endings the workspace writes with.
_PAYLOAD: Final = b64encode(SOLVED.encode("utf-8")).decode("ascii")

_EDITOR_SCRIPT: Final = (
    "import base64, pathlib, sys; "
    "pathlib.Path(sys.argv[1]).write_bytes("
    f"base64.b64decode('{_PAYLOAD}'))"
)

#: What the file is reset to between the two halves of the test, so that the
#: save the stream sees is a real change rather than a rewrite of what is
#: already there -- and so a verdict about it would be a *failing* one, which is
#: what makes the passing verdict evidence that the editor's save is the one
#: that was graded.
WRONG = """\
def two_sum(numbers, target):
    return (0, 1)
"""


@pytest.fixture
def services(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Services:
    """The real object graph over disposable storage, with a fast tick.

    The *real* content root, like the other browser end-to-end test: this is one
    of the two tests that should break if the shipped library stops being
    solvable through the web app.

    `PRACTICE_EDITOR` is set before the graph is built, because
    `SubprocessEditorLauncher` captures the environment once at construction --
    which is the adapter's own documented behaviour and the reason a test that
    patched it afterwards would be testing nothing.
    """
    monkeypatch.setenv(EDITOR_ENV, f'"{sys.executable}" -I -c "{_EDITOR_SCRIPT}"')
    built = build_services(
        content=content_root(),
        workspaces=tmp_path / "ws",
        database=tmp_path / "practice.db",
    )
    # The watcher's tick is fifteen seconds in production, which is right for an
    # idle browser tab and far too long to wait for twice in a test. Replaced
    # rather than passed through `build_services`, which takes no watcher
    # argument: the tick is this adapter's own tuning rather than a dependency
    # of the graph, and `Services` is a frozen dataclass of ports precisely so
    # that swapping one is a `replace` and not a rewiring.
    return replace(built, watcher=WatchfilesFileWatcher(_TICK))


@pytest.fixture
def client(services: Services) -> Iterator[TestClient]:
    with TestClient(create_app(services), base_url=ORIGIN, headers=BROWSER) as client:
        yield client


def a_request() -> Request:
    """A connected ASGI request, which is all `stream` wants of one: it asks
    `is_disconnected()` on every tick and builds no URLs.
    """

    async def receive() -> dict[str, str]:  # pragma: no cover - never awaited
        return {"type": "http.request"}

    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/watch",
            "headers": [(b"host", b"127.0.0.1")],
            "query_string": b"",
        },
        receive,
    )


def wait_for(path: Path, expected: str) -> None:
    """Block until `path` holds `expected`, or fail saying it never did.

    This is what separates "the editor did not run" from "the watcher did not
    notice", and it is worth the eight lines: both failures otherwise look like
    one timeout, and they are fixed in different files.
    """
    deadline = time.monotonic() + _PATIENCE
    while time.monotonic() < deadline:
        if path.is_file() and path.read_text(encoding="utf-8") == expected:
            return
        time.sleep(0.05)
    pytest.fail(f"{path} was never written by the editor")


async def verdict_from_the_first_save(services: Services, attempt_id: str) -> str:
    """Open the stream, let the editor save once, and return what was streamed.

    The editor is launched *after* the first tick rather than before the stream
    is opened, and the ordering is the thing this helper exists to get right: a
    file written before the watcher is listening produces no event at all, and a
    test that wrote first would hang waiting for a save that had already
    happened.
    """
    templates = Jinja2Templates(directory=templates_root())
    reveal = services.reveal_solution_file
    parsed = AttemptId.parse(attempt_id)
    written: list[str] = []
    async with asyncio.timeout(_PATIENCE):
        events = stream(services, templates, a_request(), attempt_id)
        async for chunk in events:
            written.append(chunk)
            if len(written) == 1:
                # The first tick means the watcher is listening; only now is a
                # save guaranteed to be seen. A file written before `awatch`
                # starts produces no event at all, and a test that saved first
                # would wait out its timeout for something that had already
                # happened.
                assert chunk.startswith(": ping")
                revealed = await asyncio.to_thread(reveal, parsed)
                assert revealed.launched, revealed.detail
                await asyncio.to_thread(wait_for, revealed.path, SOLVED)
                continue
            if "event: verdict" in chunk:
                break
        await events.aclose()
    return "".join(written)


def test_a_kata_is_solved_in_an_editor_and_graded_in_the_browser(
    client: TestClient, services: Services
) -> None:
    started = client.post(
        "/attempt", data={"exercise_id": TWO_SUM}, follow_redirects=False
    )
    assert started.status_code == 303
    attempt_id = started.headers["location"].removeprefix("/attempt/")
    parsed = AttemptId.parse(attempt_id)

    # The page offers the file, and the panel it returns names the real path in
    # the real workspace -- which is the whole of the reveal: a path a program
    # this app did not write can open. The editor really is started, which the
    # file then holding something the browser never sent is the proof of.
    panel = client.post(
        f"/api/attempt/{attempt_id}/editor", data={"source": "# not this\n"}
    )
    assert panel.status_code == 200
    assert "stub.py" in panel.text

    solution = services.provisioner.attach(
        services.content.get(ExerciseId(TWO_SUM)),  # type: ignore[arg-type]
        parsed,
    )
    assert solution is not None
    path = solution.resolve("stub.py")
    wait_for(path, SOLVED)

    # Reset it, so the save the stream sees is a change -- and one whose *old*
    # content would have failed, which is what makes the passing verdict below
    # evidence about what the editor wrote rather than about what was already
    # there.
    path.write_text(WRONG, encoding="utf-8", newline="")

    # Now the loop: a real save by a real editor, noticed by a real watcher,
    # graded by a real pytest run, streamed as the same verdict fragment the
    # page would have shown for a submission.
    streamed = asyncio.run(verdict_from_the_first_save(services, attempt_id))

    assert "event: source" in streamed
    assert "data: def two_sum(numbers, target):" in streamed
    assert "data:     seen = {}" in streamed
    assert "Finds the two positions" in streamed
    # `pass_with_advisories`, not `pass`, and it is right: the complexity claim
    # is something the solver declares *when they submit*, so a preview has none
    # and the advisory says so. Every required check passed, which is what the
    # outcome's `passed` half means -- and the standing reminder to name the cost
    # is the §4.4 advisory mechanism doing its job rather than noise.
    assert '<p class="outcome pass_with_advisories">' in streamed
    assert "not declared" in streamed

    # And nothing about it was recorded. Grade-on-save is a preview (ADR 0013):
    # the attempt is still open and its log has no solution in it.
    attempt = services.attempts.get(parsed)
    assert attempt is not None
    assert attempt.is_active
    assert not [event for event in attempt.events if isinstance(event, SolutionSaved)]

    # Submitting is still something the solver does on purpose. The source comes
    # from the browser, which has been mirroring the file -- and the file is what
    # the editor wrote, so this closes the attempt on the code that was graded.
    graded = client.post(
        f"/api/attempt/{attempt_id}/submit",
        data={"source": SOLVED, "time": "O(n)", "space": "O(n)"},
    )
    assert graded.status_code == 200
    assert '<p class="outcome pass">' in graded.text

    submitted = services.attempts.get(parsed)
    assert submitted is not None
    assert not submitted.is_active
    # Exactly one, for the one submission -- not one per save.
    saved = [event for event in submitted.events if isinstance(event, SolutionSaved)]
    assert len(saved) == 1
