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
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Form
from starlette.requests import Request  # noqa: TC002  (FastAPI reads this at runtime)
from starlette.responses import HTMLResponse, Response

from practice.application.errors import ApplicationError
from practice.domain.errors import DomainError
from practice.domain.ids import AttemptId

if TYPE_CHECKING:
    from fastapi.templating import Jinja2Templates

    from practice.composition import Services

__all__ = ["EDITOR_URL", "build_router"]

#: Where the page asks for its file to be revealed. The template builds the
#: attempt's own URL from this, so the route and the page cannot disagree about
#: the path -- the same reason `SUBMIT_URL` and `COMMAND_URL` are constants.
EDITOR_URL = "/api/attempt/{attempt_id}/editor"


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

    return router
