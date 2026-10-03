"""Own-editor mode: hand the solver their file, and open their editor on it.

A third route module under `/attempt/{id}`, on the same division as the other
two: `attempt.py` owns the page, `console.py` owns the git scenario's endpoints,
and this owns the kata's other editor. It is a separate module rather than two
more endpoints on `attempt.py` because the thing it serves is a different
*surface* — not a textarea in the page but a file on disk and a program this app
did not write — and because the file-mode panel is the one fragment on the page
that is about something outside the browser.

**The reveal is a POST, and it carries the editor's contents.** Two reasons, and
the first is enough on its own: it writes. Someone who typed into the browser
editor and then decided to switch must not lose it, so the page sends what is on
screen and the use case writes it into the file before the editor opens on it.
A GET that did that would be a GET a browser is entitled to prefetch — the same
argument `attempt.py` makes about revealing a hint.

**A launch that failed is still a 200 with a path in it.** The fragment says
where the file is either way, and whether the editor was opened. That is not
leniency: the feature is *your solution is a real file, here is where it is*,
and the only thing a launch failure costs is the convenience of not having to
open it yourself. `EditorLauncher` returns the problem rather than raising it so
that this route has something to render rather than something to catch.

**The watch endpoint is server-sent events, and it is the one `async def` in
this app.** Every other endpoint is a blocking `def` that Starlette runs in a
threadpool, which is right for something that waits two seconds on a subprocess
and wrong for something that holds a connection open for an hour: a thread per
open tab, doing nothing. So this one is async, and the blocking work inside it —
the pytest run, the SQLite read — is pushed to a thread by the use case itself.

**Native `EventSource`, not an htmx extension.** htmx 2 moved SSE out of the
core into `htmx-ext-sse`, so using the attribute form would mean a fifth
hash-pinned vendored asset (§8.2) for one panel on one page. The page already
hand-wires its submission in a `<script>`, because CodeMirror forced that in
Phase 7, so the honest comparison is four lines of `addEventListener` against a
new third-party file to download, pin, review and keep. The four lines won.

**A refusal is a 200 stream carrying a `problem` event, never a 4xx.** This is
the one place in the app where that rule is not about htmx: `EventSource`
*reconnects on its own* after a failed response, forever, with no way to say
"don't". A refusal sent as 404 would turn one unopenable attempt into a request
every three seconds for as long as the tab is open. So the stream opens, says
what is wrong, says `done`, and the page closes it.

**Every payload is HTML or plain text, and `data:` is emitted one line at a
time.** The SSE wire format makes a bare newline a field separator, so a
multi-line fragment has to be split and the client rejoins it — which is the
protocol working as designed, not a workaround. What crosses is the same verdict
partial the page includes and the submission returns (§8.4: fragments, not
JSON), plus the file's own text so the browser editor can mirror it.
"""

from __future__ import annotations

from contextlib import aclosing
from typing import TYPE_CHECKING, Annotated, Final

from fastapi import APIRouter, Form
from starlette.requests import Request  # noqa: TC002  (FastAPI reads this at runtime)
from starlette.responses import HTMLResponse, Response, StreamingResponse

from practice.application.errors import ApplicationError
from practice.domain.errors import DomainError
from practice.domain.ids import AttemptId

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi.templating import Jinja2Templates

    from practice.application.dto import Draft
    from practice.composition import Services

__all__ = [
    "EDITOR_URL",
    "SSE_MEDIA_TYPE",
    "WATCH_URL",
    "build_router",
    "sse_event",
    "stream",
]

#: Where the page asks for its file to be revealed. The template builds the
#: attempt's own URL from this, so the route and the page cannot disagree about
#: the path -- the same reason `SUBMIT_URL` and `COMMAND_URL` are constants.
EDITOR_URL = "/api/attempt/{attempt_id}/editor"

#: Where the page opens its event stream. A GET, because it changes nothing: a
#: save is the solver's action and this only reports it. That also means it is a
#: safe method as far as `SameOriginMiddleware` is concerned, and passes on the
#: loopback `Host` check alone -- which is the right outcome, since `EventSource`
#: sends no `Origin` and a page that can read our HTML can read this.
WATCH_URL = "/api/attempt/{attempt_id}/watch"

SSE_MEDIA_TYPE: Final = "text/event-stream"

#: The source of the file, as the browser editor should now show it.
_SOURCE_EVENT: Final = "source"

#: A rendered verdict fragment, for the slot under the editor.
_VERDICT_EVENT: Final = "verdict"

#: Something went wrong, in a sentence. Followed by `done`.
_PROBLEM_EVENT: Final = "problem"

#: There will be nothing more. The page closes the stream on it, which is the
#: only way to stop `EventSource` reconnecting on its own.
_DONE_EVENT: Final = "done"

#: A comment line. The wire format allows it and clients ignore it, which makes
#: it the standard SSE keepalive -- and here it is load-bearing in one direction
#: that is easy to miss: writing it is how a stream whose reader has gone away
#: finds out, because the write is what fails.
_PING: Final = ": ping\n\n"


def sse_event(name: str, payload: str = "") -> str:
    """One event, framed for the wire.

    One `data:` line per line of payload, because the format says so: a bare
    newline inside a field would end the event, and the client joins the lines
    back with `\n`. Carriage returns are normalised out first -- `CR` is a line
    terminator in SSE too, so a payload that still had them would arrive split
    in places nothing put a split.
    """
    body = payload.replace("\r\n", "\n").replace("\r", "\n")
    lines = "".join(f"data: {line}\n" for line in body.split("\n"))
    return f"event: {name}\n{lines}\n"


def build_router(services: Services, templates: Jinja2Templates) -> APIRouter:
    """The file-mode panel, closed over the services it drives."""
    router = APIRouter()

    @router.post(EDITOR_URL, response_class=HTMLResponse)
    def reveal(
        request: Request, attempt_id: str, source: Annotated[str, Form()]
    ) -> Response:
        """Write the editor's contents to the file, then open it.

        Blocking, like every endpoint in this app, and here that is the whole
        point: `SubprocessEditorLauncher` starts a process and does not wait for
        it, so what is being blocked on is one `Popen` and one file write.
        Starlette runs a `def` endpoint in a threadpool, so even a `code` shim
        that takes half a second to hand off does not stall the event loop.

        A refusal lands in the same slot as the panel, because that is where the
        person who pressed the button is looking. Every sentence it can carry is
        already written to be read -- *this attempt is completed*, *it is a git
        scenario, so there is no solution file* -- so none of them is rephrased
        here.
        """
        try:
            parsed = AttemptId.parse(attempt_id)
            revealed = services.reveal_solution_file(parsed, source)
        except (ApplicationError, DomainError, ValueError) as exc:
            return templates.TemplateResponse(
                request=request,
                name="partials/file-refusal.html",
                context={"detail": str(exc)},
            )

        return templates.TemplateResponse(
            request=request,
            name="partials/file-mode.html",
            context={"revealed": revealed},
        )

    @router.get(WATCH_URL)
    async def watch(request: Request, attempt_id: str) -> Response:
        """Stream a verdict every time the solver saves their file.

        The response is opened unconditionally, including for an attempt that
        cannot be watched: see the module docstring on why a 4xx here is worse
        than a refusal inside a 200.
        """
        return StreamingResponse(
            stream(services, templates, request, attempt_id),
            media_type=SSE_MEDIA_TYPE,
            # No store, and not merely no cache: a verdict is about a file as it
            # was one second ago, and there is no version of it worth keeping.
            headers={"Cache-Control": "no-store"},
        )

    return router


async def stream(
    services: Services,
    templates: Jinja2Templates,
    request: Request,
    attempt_id: str,
) -> AsyncGenerator[str]:
    """The event stream for one attempt, from opening to `done`.

    A module-level function rather than a closure inside the endpoint, so a test
    can drive it directly: an SSE endpoint read through a test client is a
    connection somebody has to remember to close, and what is worth asserting is
    the sequence of events rather than HTTP's part in delivering them. Named
    publicly for the same reason `kata.mechanism_files` is, and typed as the
    generator it is rather than as an iterator, so a caller that takes the
    events it needs can `aclose()` the rest.
    """
    try:
        drafts = services.watch_solution_file(AttemptId.parse(attempt_id))
    except (ApplicationError, DomainError, ValueError) as exc:
        yield sse_event(_PROBLEM_EVENT, str(exc))
        yield sse_event(_DONE_EVENT)
        return

    # `aclosing`, and not merely a `for` loop: that generator holds a live file
    # watch, and leaving it to be garbage collected leaves the watch running for
    # as long as that takes. Closing it on the way out of this block is what
    # makes a closed browser tab release its watcher, which is the whole reason
    # the port yields ticks.
    try:
        async with aclosing(drafts) as saves:
            async for draft in saves:
                if draft is None:
                    # A tick. The disconnect check is cheap and explicit; the
                    # ping that follows is the one that would fail on a dead
                    # socket, and between them they are how an abandoned stream
                    # ends rather than running until the server stops.
                    if await request.is_disconnected():
                        return
                    yield _PING
                    continue
                # The source first: when the verdict lands, the editor is
                # already showing the code it is about.
                yield sse_event(_SOURCE_EVENT, draft.source)
                yield sse_event(_VERDICT_EVENT, _verdict_fragment(templates, draft))
    except (ApplicationError, DomainError) as exc:
        # Submitting from another tab finishes the attempt, and the aggregate's
        # refusal is how this stream learns that -- which is a normal end, not a
        # failure, so it is reported in the stream and not raised through it.
        yield sse_event(_PROBLEM_EVENT, str(exc))

    yield sse_event(_DONE_EVENT)


def _verdict_fragment(templates: Jinja2Templates, draft: Draft) -> str:
    """`partials/verdict.html`, rendered to a string.

    The verdict partial and not `partials/graded.html`: that one wraps the
    schedule control, and a *draft* has nothing to schedule -- the attempt has
    not finished, and `OfferReview` refuses one with no verdict. This is the
    same file the page includes and the submission returns, which is what makes
    a preview and a submission describe one solution the same way.

    Rendered without a `Request`, which `TemplateResponse` would require and
    this does not have a use for: the partial builds no URLs. `get_template`
    plus `render` is the plainer call, and it keeps the SSE framing the only
    thing this module does with the output.
    """
    return templates.get_template("partials/verdict.html").render(verdict=draft.verdict)
