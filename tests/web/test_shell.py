"""The layout and the dashboard: what every page is built on top of.

Assertions on rendered HTML, not on a parse tree. The alternative is a DOM
library, and for a server-rendered page the substring is the honest check:
`hx-post="/api/..."` either appears in what the browser receives or it does not,
and a selector that matched a restructured template would hide exactly the break
worth catching.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.ids import ExerciseId

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.web.conftest import Wiring


def test_the_dashboard_renders(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_the_layout_loads_every_asset_from_disk(client: TestClient) -> None:
    """Belt to `test_offline.py`'s braces, from the other side.

    That file greps the template; this asserts on what a browser is actually
    served, which is the thing that matters and is not quite the same statement —
    a Jinja2 `url_for` could in principle render an absolute URL.
    """
    body = client.get("/").text

    assert '/static/vendor/htmx.min.js"' in body
    assert '/static/app.css"' in body
    assert "http://" not in body
    assert "https://" not in body


def test_the_dashboard_counts_the_library(client: TestClient) -> None:
    """Two exercises are wired, and the page says two rather than a placeholder."""
    body = client.get("/").text

    assert "2 exercises" in body


def test_an_open_attempt_is_a_link_to_its_workbench(
    client: TestClient, wiring: Wiring
) -> None:
    """The reason §11 deferred prefix matching on the CLI.

    *"Accepting a prefix would need a `find_by_prefix` on the `AttemptRepository`
    port … The web app is where the id is in a link nobody types."* This is that
    link, and it carries the full uuid for the same reason `practice attempts`
    prints one.
    """
    started = wiring.services.start_attempt(ExerciseId("katas/two-sum"))

    body = client.get("/").text

    assert f'href="/attempt/{started.attempt.id}"' in body
    assert "Two Sum" in body


def test_an_attempt_whose_workspace_is_gone_is_not_offered_as_a_link(
    client: TestClient, wiring: Wiring
) -> None:
    """Offering a link that cannot work is what `can_resume` exists to prevent.

    The DTO already knows the answer — `OpenAttempt.can_resume` joins the attempt
    to whether its directory is still there — so the template asks rather than
    guessing, and the page says the one thing left to do about it.
    """
    started = wiring.services.start_attempt(ExerciseId("katas/two-sum"))
    wiring.provisioner.collect(started.attempt.id)

    body = client.get("/").text

    assert f'href="/attempt/{started.attempt.id}"' not in body
    assert "can only be abandoned" in body


def test_the_dashboard_says_so_when_nothing_is_open(client: TestClient) -> None:
    """Which is the normal state: an attempt closes itself when it is submitted."""
    body = client.get("/").text

    assert "Nothing open" in body


def test_the_dashboard_no_longer_promises_a_later_phase(client: TestClient) -> None:
    """The tripwire that was here until Phase 9, inverted.

    Until the scheduler existed this page carried a section saying due-today and
    a streak were *"phase 9"*, and a test asserted that sentence was present —
    so that when the phase landed the build would fail and somebody would have to
    come back and delete the promise rather than leave it beside a working queue.
    It did fail, which is the whole value of the device; what is left is the other
    half, so the promise cannot come back.
    """
    body = client.get("/").text

    assert "phase 9" not in body.lower()
    assert "Due today" in body
