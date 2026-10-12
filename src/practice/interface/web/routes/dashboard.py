"""`/` — what to practise now, how it is going, and what is still open.

PLAN.md §8.4 asks this page for due-today, a streak and the weakest tags, and as
of Phase 9 all three exist. The order they are rendered in is the order of the
questions somebody opening the tool actually has: *what should I do*, then *am I
keeping this up*, then *where am I losing it*.

**The queue is the whole answer and the page shows the top of it.** `ReviewQueue`
returns every exercise that is due or has never been scheduled, which on a fresh
install is the entire library; a dashboard that printed all of it would bury the
rest of the page under a list that is also one click away on `/browse`. So the
page takes the first few and says how many there are — the cut is here rather
than in the use case, because *how much fits on a panel* is a question about this
page and nothing else.

**Two reads, not one.** The queue and the progress summary both touch the card
store, and merging them was tempting until the shapes disagreed: a queue row is
an exercise with a card, and a summary row is a tag with a rate. One use case
answering both would be two use cases sharing a name.

The resume-or-abandon half stays, and stays *below* the queue. It is the web form
of §8.1's rule and it is also, usually, empty — a section whose normal state is
"nothing here" does not belong at the top of a page somebody opens every day.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from fastapi import APIRouter
from starlette.requests import Request  # noqa: TC002  (FastAPI reads this at runtime)
from starlette.responses import HTMLResponse, Response

if TYPE_CHECKING:
    from fastapi.templating import Jinja2Templates

    from practice.composition import Services

__all__ = ["QUEUE_LIMIT", "build_router"]

#: How many queue rows the dashboard shows. Six is about a screen's worth beside
#: the progress panel, and the page prints the total either way so the cut never
#: hides the size of what is waiting.
QUEUE_LIMIT: Final = 6


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
        queue = services.review_queue()
        open_attempts = services.list_open_attempts()
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "title": "Practice",
                "exercise_count": len(services.content.list_exercises()),
                "open_attempts": open_attempts,
                "queue": queue[:QUEUE_LIMIT],
                "queue_total": len(queue),
                "progress": services.summarise_progress(),
                # Per exercise, from the attempt log: what makes a queue row
                # say "passed 2026-10-09" instead of "new" for an exercise that
                # was solved and never given a schedule grade.
                "records": services.recall_exercises(),
                "tracks": services.follow_tracks(),
                # The same join `/browse` makes, for the same reason: starting a
                # second attempt at an exercise that already has one open would
                # provision a second workspace and split the budget across two
                # attempts that look like one piece of work.
                "open_by_exercise": {
                    open_attempt.attempt.exercise_id: open_attempt
                    for open_attempt in open_attempts
                    if open_attempt.can_resume
                },
            },
        )

    return router
