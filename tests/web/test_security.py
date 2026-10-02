"""The guards of PLAN.md §8.3, and the one it does not name.

This is the detail §14 lists as *"a security detail most people miss"*, so the
tests are written to be the argument rather than to cover the lines: binding to
localhost does not stop a page in your browser from POSTing to
`http://127.0.0.1:8765`, and a server that runs `git` and `pytest` on request is
not a server to be relaxed about.

The refusal cases POST to `/attempt`, the route that starts one, because that is
the request an attacker would actually want to make. They assert the *refusal*, so
they hold whether or not that route is wired yet — the guard is middleware and runs
before routing, which `test_the_guard_runs_before_routing` pins directly.

The third guard — a loopback `Host` — is the finding from writing the other two.
`test_a_rebound_hostname_is_refused_although_both_other_guards_pass` is the whole
reason it exists: under DNS rebinding the browser truthfully reports
`Sec-Fetch-Site: same-origin` and an `Origin` that matches, because as far as it
is concerned the page and the server share an origin. Only the hostname gives it
away.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

from practice.interface.web.security import (
    LOOPBACK_HOSTS,
    SAFE_METHODS,
    NotLoopbackError,
    is_loopback,
    require_loopback,
)

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

# --- loopback binding ------------------------------------------------------


@pytest.mark.parametrize(
    "host", ["127.0.0.1", "localhost", "::1", "[::1]", "127.0.0.1:8765", "LocalHost"]
)
def test_a_loopback_host_is_allowed(host: str) -> None:
    assert is_loopback(host)
    assert require_loopback(host) == host


@pytest.mark.parametrize(
    "host",
    [
        "0.0.0.0",  # noqa: S104  (the exact value this test exists to refuse)
        "",
        "192.168.1.14",
        "practice.example",
        "evil.example:8765",
        "127.0.0.1.evil.example",
        "localhost.evil.example",
    ],
)
def test_anything_else_is_refused(host: str) -> None:
    assert not is_loopback(host)
    with pytest.raises(NotLoopbackError):
        require_loopback(host)


def test_the_refusal_says_what_is_allowed() -> None:
    """A refusal whose message does not name the alternative is a puzzle."""
    with pytest.raises(NotLoopbackError, match=re.escape("127.0.0.1")) as caught:
        require_loopback("0.0.0.0")  # noqa: S104  (deliberate)

    assert "arbitrary code" in str(caught.value)


def test_a_bare_ipv6_literal_is_not_mistaken_for_a_host_and_port() -> None:
    """`::1` has colons in it and no port, and splitting on the last one breaks it.

    Pinned because the obvious implementation -- `rsplit(':', 1)[0]` -- turns
    `::1` into `::` and rejects the loopback address it is supposed to allow.
    """
    assert is_loopback("::1")
    assert is_loopback("[::1]:8765")


# --- the cross-origin guard ------------------------------------------------


def test_a_browser_request_from_our_own_page_is_allowed(client: TestClient) -> None:
    """The baseline, so the refusals below are about the headers and not the route."""
    assert client.get("/").status_code == 200


def test_a_mutating_request_with_no_origin_at_all_is_refused(
    bare_client: TestClient,
) -> None:
    """The strict reading, and the one decision in the middleware.

    The lenient alternative -- no `Origin` and no `Sec-Fetch-Site` means a
    non-browser client, so allow it -- hands the entire guard to any browser that
    omits the header. Browsers have sent `Origin` on every non-GET fetch for years,
    so the strict rule costs a browser nothing and costs `curl -X POST` a header.
    """
    response = bare_client.post("/attempt", data={"exercise_id": "katas/two-sum"})

    assert response.status_code == 403
    assert "refused" in response.text


def test_a_mutating_request_from_another_site_is_refused(
    bare_client: TestClient,
) -> None:
    """The attack §8.3 describes: a page you visited, POSTing to your dev server."""
    response = bare_client.post(
        "/attempt",
        data={"exercise_id": "katas/two-sum"},
        headers={"origin": "http://evil.example", "sec-fetch-site": "cross-site"},
    )

    assert response.status_code == 403


def test_an_origin_header_alone_is_enough_when_it_matches(
    bare_client: TestClient,
) -> None:
    """Either signal suffices on its own.

    `Sec-Fetch-Site` is what a modern browser sends and `Origin` is what a
    cross-origin request would have to forge, so requiring both would reject an
    older browser for being old rather than for being wrong.

    Asserted as a 404 rather than a 2xx: the point is that the request reached
    *routing*, and tying this case to whichever mutating route happens to exist
    would make it a test of that route instead.
    """
    response = bare_client.post(
        "/does-not-exist", headers={"origin": "http://127.0.0.1"}
    )

    assert response.status_code == 404


def test_the_guard_runs_before_routing(bare_client: TestClient) -> None:
    """A refused request never reaches a handler, including a missing one.

    Worth pinning because the order is what makes the guard total: a check
    implemented as a per-route dependency would let a POST to an unrouted path
    answer 404, and "which paths 404" is a map of the app handed to a page that
    was not allowed to ask.
    """
    assert bare_client.post("/does-not-exist").status_code == 403


def test_sec_fetch_site_is_believed_over_a_matching_origin(
    bare_client: TestClient,
) -> None:
    """A page cannot set `Sec-Fetch-Site`; it can set `Origin` on a server-side
    request. So when the browser's own header says cross-site, a matching `Origin`
    does not rescue it -- checking `Origin` first would let a forged pair through.
    """
    response = bare_client.post(
        "/attempt",
        data={"exercise_id": "katas/two-sum"},
        headers={"origin": "http://127.0.0.1", "sec-fetch-site": "cross-site"},
    )

    assert response.status_code == 403


@pytest.mark.parametrize("method", sorted(SAFE_METHODS))
def test_a_safe_method_is_not_subject_to_the_origin_rule(
    bare_client: TestClient, method: str
) -> None:
    """A cross-origin GET reads our HTML, which it can already do.

    Refusing it would buy nothing -- the browser would not hand the body to the
    other page anyway, without CORS headers this app does not send -- and would
    break opening a bookmark, where `Sec-Fetch-Site` is `none`.
    """
    response = bare_client.request(method, "/")

    assert response.status_code != 403


# --- the guard §8.3 does not name -----------------------------------------


def test_a_rebound_hostname_is_refused_although_both_other_guards_pass(
    bare_client: TestClient,
) -> None:
    """DNS rebinding, which the §8.3 pair cannot see.

    If `evil.example` resolves to 127.0.0.1, a page served from it sends
    `Origin: http://evil.example` to a request whose own `Host` is `evil.example`
    -- so the two agree -- and `Sec-Fetch-Site: same-origin`, truthfully, because
    the browser considers them one origin. Both named guards pass. The hostname is
    the only thing that gives it away, which is why the `Host` check exists and
    why it applies to reads as well as writes.
    """
    response = bare_client.post(
        "/attempt",
        data={"exercise_id": "katas/two-sum"},
        headers={
            "host": "evil.example",
            "origin": "http://evil.example",
            "sec-fetch-site": "same-origin",
        },
    )

    assert response.status_code == 421


def test_the_host_check_applies_to_reads_too(bare_client: TestClient) -> None:
    """A rebound page that can read our HTML can read an attempt's transcript."""
    response = bare_client.get("/", headers={"host": "evil.example"})

    assert response.status_code == 421


@pytest.mark.parametrize("host", sorted(LOOPBACK_HOSTS))
def test_every_allowed_host_really_is_served(
    bare_client: TestClient, host: str
) -> None:
    """So the `Host` check cannot pass by refusing everything.

    Each spelling in `LOOPBACK_HOSTS` is one someone will actually type into a
    browser or a `--host` flag, and a guard that rejected `localhost` would be
    discovered by a user rather than by this file.
    """
    response = bare_client.get("/", headers={"host": host})

    assert response.status_code == 200


def test_a_refusal_does_not_say_which_guard_tripped(bare_client: TestClient) -> None:
    """Both refusals read the same, deliberately.

    A body that explained the difference would be a tool for finding the guard
    that does not refuse. The person who needs the explanation is reading
    `security.py`.
    """
    rebound = bare_client.get("/", headers={"host": "evil.example"})
    foreign = bare_client.post("/attempt", headers={"origin": "http://evil.example"})

    assert rebound.text == foreign.text
