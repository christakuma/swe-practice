"""`/` — what the library holds, and what is still open.

PLAN.md §8.4 wants due-today, a streak and the weakest tags on this page, and all
three are Phase 9's progress model. What it can honestly show now is the two
things that exist: how large the library is, and which attempts have been neither
submitted nor abandoned.

That second half is not filler. It is the web form of the resume-or-abandon rule
of §8.1, and it is a better form than the CLI's: `practice attempts` prints a uuid
nobody can type, and the reason §11 gave for deferring prefix matching was that
*"the web app, where the id is in a link nobody types, is Phase 7."* This is that
link.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter
from starlette.requests import Request  # noqa: TC002  (FastAPI reads this at runtime)
from starlette.responses import HTMLResponse, Response

if TYPE_CHECKING:
    from fastapi.templating import Jinja2Templates

    from practice.composition import Services

__all__ = ["build_router"]


def build_router(services: Services, templates: Jinja2Templates) -> APIRouter:
    """The dashboard, closed over the services it reads."""
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> Response:
        """Synchronous on purpose, and every route in this app is.

        Starlette runs a `def` endpoint in a threadpool, so a request that spends
        ten seconds inside `git` or `pytest` does not block the event loop. An
        `async def` would — every use case under here is blocking, by design
        (`subprocess`, `sqlite3`), and wrapping blocking work in a coroutine is
        the one way to make a single-user local app unresponsive.
        """
        exercises = services.content.list_exercises()
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "title": "Practice",
                "exercise_count": len(exercises),
                "open_attempts": services.list_open_attempts(),
            },
        )

    return router
