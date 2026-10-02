"""Two and a half guards on a server that executes arbitrary code by design.

PLAN.md §8.3 names two, and both are small:

1. **Loopback binding.** Startup refuses any host that is not a loopback
   address, so a change to `0.0.0.0` fails at the point it is made rather than
   in a hotel's wifi six months later.
2. **Cross-origin guard.** Binding to localhost does *not* stop a malicious page
   in your browser from POSTing to `http://127.0.0.1:8765` — the browser will
   happily make that request, and the fact that nobody outside can reach the port
   is irrelevant when the attacker is already running code inside the machine
   that can. Mutating requests must prove they came from our own page.

**The half is a `Host` check, and it is the finding from writing this.** §8.3's
pair does not cover DNS rebinding, and the reason is worth stating because it is
the opposite of obvious: if `evil.example` resolves to `127.0.0.1`, a page served
from it sends `Origin: http://evil.example` to a request whose own
`Host: evil.example`, so the two *agree* — and `Sec-Fetch-Site` says
`same-origin`, truthfully, because as far as the browser is concerned it is. Both
guards pass. Comparing `Host` against the loopback names closes it, costs three
lines, and is the reason this module checks every request and not only the
mutating ones.

**A request that cannot prove its origin is refused, including one that says
nothing at all.** The lenient reading — no `Origin` and no `Sec-Fetch-Site` means
a non-browser client, so allow it — is how most localhost tools do this, and it
hands the whole guard to any browser that omits the header. Browsers have sent
`Origin` on every non-GET fetch for years and `Sec-Fetch-Site` on everything for
several, so the strict rule costs a browser nothing. What it costs is `curl -X
POST` without a header, which is the right thing to charge: there is a CLI for
that, over the same use cases, and it does not need a server at all.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final
from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from starlette.requests import Request
    from starlette.responses import Response

__all__ = [
    "LOOPBACK_HOSTS",
    "SAFE_METHODS",
    "NotLoopbackError",
    "SameOriginMiddleware",
    "is_loopback",
    "require_loopback",
]

#: The hostnames this app will bind to and answer for. Spelled out rather than
#: resolved, because resolution is the thing being defended against: `localhost`
#: is in the list as a name a human types, and anything else that happens to
#: point at 127.0.0.1 is not.
LOOPBACK_HOSTS: Final = frozenset({"127.0.0.1", "localhost", "::1", "[::1]"})

#: Methods that cannot change anything, so they are not what the cross-origin
#: rule is about. A cross-origin `GET` is a page reading our HTML, which it can
#: do; a cross-origin `POST` starts an attempt or runs a grader.
SAFE_METHODS: Final = frozenset({"GET", "HEAD", "OPTIONS"})

#: What a refusal says. Deliberately the same body for every reason: a response
#: that explained which guard tripped would be a tool for finding the one that
#: does not, and the person who needs the explanation is reading this file.
_REFUSED: Final = "refused: this request did not come from the practice app\n"


class NotLoopbackError(ValueError):
    """The server was asked to bind somewhere it must not.

    A `ValueError` because the host is an argument that is wrong, and raised at
    startup rather than reported per request: a server listening on `0.0.0.0` has
    already published a code-execution endpoint to the network by the time the
    first request arrives.
    """


def is_loopback(host: str) -> bool:
    """Whether `host` names this machine and only this machine.

    A port is stripped if one is present, so the same function answers for a
    `--host` argument and for a `Host` header.
    """
    return _hostname(host) in LOOPBACK_HOSTS


def require_loopback(host: str) -> str:
    """`host` if it is a loopback address, else raise.

    Returns it so a caller can write `uvicorn.run(app, host=require_loopback(h))`
    and have the check be unskippable rather than a line above that someone
    deletes while rebasing.
    """
    if not is_loopback(host):
        raise NotLoopbackError(
            f"refusing to bind to {host!r}: this server runs arbitrary code by "
            f"design, so it listens on loopback only. Allowed: "
            f"{', '.join(sorted(LOOPBACK_HOSTS))}."
        )
    return host


class SameOriginMiddleware(BaseHTTPMiddleware):
    """Refuse requests that cannot prove they came from this app's own pages.

    Two rules, in the order they are cheap to evaluate:

    * **Every** request must carry a loopback `Host`. This is the DNS-rebinding
      half described in the module docstring, and it has to apply to `GET` too —
      a rebound page that can read our HTML can read an attempt's transcript out
      of it.
    * **Mutating** requests must additionally carry either
      `Sec-Fetch-Site: same-origin` or an `Origin` equal to the one they arrived
      at. Either is sufficient on its own: the first is what a modern browser
      sends and the second is what a cross-origin request would have to forge.

    `BaseHTTPMiddleware` rather than a dependency on each route, because a guard
    you have to remember to attach is a guard that will be missing from the route
    added in a hurry — the same argument `tests/conftest.py` makes for applying
    markers by directory.
    """

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if not is_loopback(request.headers.get("host", "")):
            return PlainTextResponse(_REFUSED, status_code=421)
        if request.method in SAFE_METHODS:
            return await call_next(request)
        if not _proves_same_origin(request):
            return PlainTextResponse(_REFUSED, status_code=403)
        return await call_next(request)


def _proves_same_origin(request: Request) -> bool:
    """Whether a mutating request carries positive evidence of its own origin.

    `Sec-Fetch-Site` is checked first because it is the header a browser sets and
    a page cannot: `fetch` and `XMLHttpRequest` both refuse to override a
    `Sec-` prefixed name, so its presence is the browser's own statement.
    """
    site = request.headers.get("sec-fetch-site")
    if site is not None:
        return site == "same-origin"

    origin = request.headers.get("origin")
    if origin is None:
        return False
    return _origin_of(origin) == _origin_of(str(request.base_url))


def _origin_of(url: str) -> tuple[str, str]:
    """Scheme and authority, which is what "same origin" compares.

    The path is dropped — `request.base_url` carries one and an `Origin` header
    never does, so comparing the strings would never match.
    """
    parts = urlsplit(url)
    return parts.scheme, parts.netloc


def _hostname(host: str) -> str:
    """`127.0.0.1:8765` -> `127.0.0.1`, `[::1]:8765` -> `[::1]`, `::1` -> `::1`.

    Hand-written rather than `urlsplit`, which wants a scheme before it will find
    a netloc. Three forms because three forms reach this: a `Host` header, which
    brackets an IPv6 literal; a `--host` argument, where someone types `::1`
    bare; and either with a port. Both spellings of the literal are in
    `LOOPBACK_HOSTS`, so they compare equal without being rewritten into each
    other.

    The bare-IPv6 case is why the port is not simply split off the last colon:
    `::1` would become `::`, and the guard would reject the address it is
    supposed to allow.
    """
    candidate = host.strip().lower()
    if candidate.startswith("["):
        closing = candidate.find("]")
        return candidate[: closing + 1] if closing != -1 else candidate
    if candidate.count(":") != 1:
        return candidate
    return candidate.rsplit(":", 1)[0]
