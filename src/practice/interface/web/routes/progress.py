"""`/progress` — mastery by tag, the attempt history, and the activity window.

The fourth page PLAN.md §8.4 lists, and the one that exists so the dashboard does
not have to. That page answers *what now*; this one answers *how is it going*,
which is a different question asked at a different frequency and deserves room
rather than a corner.

**One use case and no arithmetic here.** `SummariseProgress` returns everything
on the page in one pass, and the charts are Jinja filters over it — so this route
is a template name and a context, which is what every route in this app aims to
be. The temptation it resists is a second summary with a different window for the
chart; `window_days` is a parameter on the use case precisely so a future "last
90 days" control is a query string rather than a second code path.

**The history is the whole of it, not a page of it.** A local practice log is
hundreds of rows, pagination is a control nobody wants on their own history, and
the honest moment to add one is when the page is slow rather than when it is
imaginable that it could be.
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
    """The progress page, closed over the services it reads."""
    router = APIRouter()

    @router.get("/progress", response_class=HTMLResponse)
    def progress(request: Request) -> Response:
        """Synchronous, like every route here: `sqlite3` is blocking by design.

        The library comes along so the history can name an exercise rather than
        print its id. The join is made here rather than in the summary because
        `Progress` deliberately carries attempts and not exercises -- an attempt
        whose exercise has left the library still counts, and a DTO that paired
        them would have had to drop it or invent one.

        The listing is not the whole of what can be attempted: a variant is
        never in it (ADR 0028), so the ones in the history are fetched by id.
        Without that a twist is the one row on the page that prints a path
        where every other row prints a name.
        """
        summary = services.summarise_progress()
        titles = {
            exercise.id: exercise.title
            for exercise in services.content.list_exercises()
        }
        for unlisted in {attempt.exercise_id for attempt in summary.attempts} - set(
            titles
        ):
            found = services.content.get(unlisted)
            if found is not None:
                titles[unlisted] = found.title
        return templates.TemplateResponse(
            request=request,
            name="progress.html",
            context={"title": "Progress", "progress": summary, "titles": titles},
        )

    return router
