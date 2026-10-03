"""`GET /api/attempt/{id}/watch` — the event stream grade-on-save rides.

**The generator is driven directly rather than through the test client**, which
is why `_stream` is a module-level function. An SSE endpoint read over HTTP is a
connection somebody has to remember to close, and a test that forgot would hang
the suite rather than fail it; what is worth asserting here is the *sequence of
events*, and HTTP's part in delivering them is Starlette's business. One test
does go through the client, to pin the content type and the fact that a response
arrives at all.

The watcher behind these is the scripted fake, so "the solver saved" is a line
in the test rather than a race against the filesystem.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from practice.domain.ids import ExerciseId
from practice.interface.web.app import templates_root
from practice.interface.web.routes.editor import (
    SSE_MEDIA_TYPE,
    sse_event,
    stream,
)
from tests.web.conftest import ORIGIN, a_wiring

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")

SOLVED = "def two_sum(numbers, target):\n    return (0, 1)\n"


def a_connected_request() -> Request:
    """A request whose client is still there.

    Hand-built rather than captured: `_stream` asks `is_disconnected()` on every
    tick, and that reads from the ASGI `receive` channel -- so what a test has to
    supply is a channel, not a URL.
    """

    async def receive() -> dict[str, str]:  # pragma: no cover - never awaited
        return {"type": "http.request"}

    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/attempt/x/watch",
            "headers": [(b"host", b"127.0.0.1")],
            "query_string": b"",
        },
        receive,
    )


def a_disconnected_request() -> Request:
    """A request whose client has gone. The tick is where that is noticed."""

    async def receive() -> dict[str, str]:
        return {"type": "http.disconnect"}

    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/attempt/x/watch",
            "headers": [(b"host", b"127.0.0.1")],
            "query_string": b"",
        },
        receive,
    )


def events(
    wiring: Wiring, attempt_id: object, *, request: Request | None = None
) -> str:
    """Everything the stream writes for one attempt, concatenated."""
    templates = Jinja2Templates(directory=templates_root())
    connection = request if request is not None else a_connected_request()

    async def collect() -> str:
        return "".join(
            [
                chunk
                async for chunk in stream(
                    wiring.services, templates, connection, str(attempt_id)
                )
            ]
        )

    return asyncio.run(collect())


class TestTheWireFormat:
    """`sse_event`: one `data:` line per line, because the format says so."""

    def test_a_single_line_payload(self) -> None:
        assert (
            sse_event("verdict", "<p>ok</p>") == "event: verdict\ndata: <p>ok</p>\n\n"
        )

    def test_a_multi_line_payload_is_split_into_one_field_per_line(self) -> None:
        """A bare newline inside a field would end the event; the client joins
        the `data:` lines back with a newline, so nothing is lost.
        """
        assert sse_event("source", "one\ntwo") == (
            "event: source\ndata: one\ndata: two\n\n"
        )

    def test_carriage_returns_are_normalised_away(self) -> None:
        """`CR` is a line terminator in SSE too, so a payload that kept them
        would arrive split in places nothing put a split. A file saved by a
        Windows editor is exactly how one gets here.
        """
        assert sse_event("source", "one\r\ntwo\rthree") == (
            "event: source\ndata: one\ndata: two\ndata: three\n\n"
        )

    def test_an_event_with_no_payload_still_has_a_data_field(self) -> None:
        assert sse_event("done") == "event: done\ndata: \n\n"


def test_a_save_streams_the_source_and_then_the_verdict() -> None:
    """In that order: when the verdict lands, the editor is already showing the
    code it is about -- which is what makes Submit unambiguous in a mode with
    two editors.
    """
    wiring = a_wiring()
    started = wiring.services.start_attempt(KATA)
    wiring.provisioner.workspace_for(started.attempt.id).write_file("stub.py", SOLVED)
    wiring.watcher.saves()

    written = events(wiring, started.attempt.id)

    assert written.index("event: source") < written.index("event: verdict")
    assert "data: def two_sum(numbers, target):" in written
    assert "Finds the two positions" in written


def test_the_verdict_event_carries_the_same_partial_the_page_includes() -> None:
    """`partials/verdict.html` and not `partials/graded.html`: a draft has
    nothing to schedule, because the attempt has not finished.
    """
    wiring = a_wiring()
    started = wiring.services.start_attempt(KATA)
    wiring.provisioner.workspace_for(started.attempt.id).write_file("stub.py", SOLVED)
    wiring.watcher.saves()

    written = events(wiring, started.attempt.id)

    assert "verdict-summary" in written
    # The schedule block belongs to a finished attempt, and this one is live.
    assert "Schedule" not in written


def test_every_stream_ends_with_done() -> None:
    """Which is the only way to stop `EventSource` reconnecting on its own."""
    wiring = a_wiring()
    started = wiring.services.start_attempt(KATA)
    wiring.provisioner.workspace_for(started.attempt.id).write_file("stub.py", SOLVED)
    wiring.watcher.saves()

    assert events(wiring, started.attempt.id).endswith(sse_event("done"))


def test_a_tick_writes_a_keepalive_comment() -> None:
    """A comment line: ignored by every client, and the thing whose *write*
    fails on a socket whose reader has gone.
    """
    wiring = a_wiring()
    started = wiring.services.start_attempt(KATA)
    wiring.watcher.ticks(2)

    written = events(wiring, started.attempt.id)

    assert written.count(": ping") == 2


def test_a_disconnected_reader_ends_the_stream_at_the_first_tick() -> None:
    """Without this, an abandoned tab would leave a file watcher running until
    the server stopped -- which is the whole reason the port yields ticks.
    """
    wiring = a_wiring()
    started = wiring.services.start_attempt(KATA)
    wiring.provisioner.workspace_for(started.attempt.id).write_file("stub.py", SOLVED)
    wiring.watcher.ticks().saves()

    written = events(wiring, started.attempt.id, request=a_disconnected_request())

    assert ": ping" not in written
    assert "event: verdict" not in written
    # Not even `done`: there is nobody to read it.
    assert written == ""


def test_an_attempt_that_cannot_be_watched_is_refused_inside_the_stream() -> None:
    """A 200 carrying a `problem`, never a 4xx: `EventSource` retries a failed
    response forever, so a refusal sent as 404 would become a request every few
    seconds for as long as the tab is open.
    """
    wiring = a_wiring()
    started = wiring.services.start_attempt(SCENARIO)

    written = events(wiring, started.attempt.id)

    assert "event: problem" in written
    assert "no solution file" in written
    assert written.endswith(sse_event("done"))


def test_a_malformed_attempt_id_is_refused_inside_the_stream() -> None:
    wiring = a_wiring()

    written = events(wiring, "oops")

    assert "event: problem" in written
    assert "oops" in written


def test_submitting_from_another_tab_ends_the_stream_with_a_sentence() -> None:
    """The aggregate's own refusal, reported rather than raised: a stream whose
    attempt has been submitted is finished, which is a normal end.
    """
    wiring = a_wiring()
    started = wiring.services.start_attempt(KATA)
    workspace = wiring.provisioner.workspace_for(started.attempt.id)
    workspace.write_file("stub.py", SOLVED)
    wiring.services.submit_solution(started.attempt.id, SOLVED)
    wiring.watcher.saves()

    written = events(wiring, started.attempt.id)

    assert "event: problem" in written
    assert "completed" in written


def test_the_endpoint_answers_as_an_event_stream(
    client: TestClient, wiring: Wiring
) -> None:
    """The one test through HTTP, because the content type is HTTP's part of
    this: a stream served as `text/html` is a stream no `EventSource` reads.

    It asks about an attempt that cannot be watched, so the response completes
    on its own -- a live stream read through the test client would wait on the
    watcher for as long as the suite was willing to.
    """
    started = wiring.services.start_attempt(SCENARIO)

    response = client.get(f"/api/attempt/{started.attempt.id}/watch")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(SSE_MEDIA_TYPE)
    assert response.headers["cache-control"] == "no-store"
    assert "event: problem" in response.text


def test_the_workbench_tells_the_page_where_to_watch(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)

    page = client.get(f"/attempt/{started.attempt.id}")

    assert f"/api/attempt/{started.attempt.id}/watch" in page.text
    assert ORIGIN not in page.text  # a relative URL, like every other on the page
