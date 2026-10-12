"""`/tracks` and `/tracks/{name}` — a route through the library, and your place on it.

The page the other three could not be. Browse is the whole library with no
position in it; the dashboard's queue is what the scheduler wants today;
`/progress` is how it has gone. None of them answers *where was I*, and a list
of a hundred and fifteen exercises with no place marked in it is a list
somebody has to keep their own notes about.

**One use case, read whole, for both routes.** `FollowTracks` walks every
declared track against the attempt history in a single pass, the listing shows
all of them, and the detail page picks one out by name. A second read that
fetched only the named track would save the walk and repeat the query, which is
the expensive half.

**An unknown name is a 404 in the normal layout**, not a redirect to the
listing. Somebody followed a link to a track that is not here, and saying so —
with the navigation still on the page — is more use than landing them somewhere
they did not ask for with no explanation.

**Every Start on these pages posts the track's name**, which is the one thing
they do that Browse does not: it is what makes the attempt's own page know
which track to offer the next step of (`interface/web/navigation.py`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter
from starlette.requests import Request  # noqa: TC002  (FastAPI reads this at runtime)
from starlette.responses import HTMLResponse, Response

from practice.interface.web.errors import render_problem

if TYPE_CHECKING:
    from fastapi.templating import Jinja2Templates

    from practice.application.dto import OpenAttempt
    from practice.composition import Services
    from practice.domain.ids import ExerciseId

__all__ = ["build_router"]


def build_router(services: Services, templates: Jinja2Templates) -> APIRouter:
    """The two track pages, closed over the services they read."""
    router = APIRouter()

    @router.get("/tracks", response_class=HTMLResponse)
    def tracks(request: Request) -> Response:
        return templates.TemplateResponse(
            request=request,
            name="tracks.html",
            context={
                "title": "Tracks",
                "tracks": services.follow_tracks(),
                "open_by_exercise": _open_by_exercise(services),
            },
        )

    @router.get("/tracks/{name}", response_class=HTMLResponse)
    def track(request: Request, name: str) -> Response:
        found = next(
            (
                progress
                for progress in services.follow_tracks()
                if progress.track.name == name
            ),
            None,
        )
        if found is None:
            return render_problem(
                templates,
                request,
                title="No such track",
                detail=f"This library has no track called {name!r}.",
                status=404,
            )
        return templates.TemplateResponse(
            request=request,
            name="track.html",
            context={
                "title": found.track.title,
                "progress": found,
                "open_by_exercise": _open_by_exercise(services),
            },
        )

    return router


def _open_by_exercise(services: Services) -> dict[ExerciseId, OpenAttempt]:
    """The join `/browse` makes, for the reason it makes it: a step with an
    attempt already open is offered as Resume, because a second Start would
    provision a second workspace for what the solver thinks of as one attempt.
    """
    return {
        found.attempt.exercise_id: found
        for found in services.list_open_attempts()
        if found.can_resume
    }
