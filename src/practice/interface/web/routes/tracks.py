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

**The detail page is searchable and carries an optional goal.** `?q=` and
`?show=todo|done` are a plain GET form: a hundred and forty-four steps with no
way to narrow them was the complaint, and a form needs none of the script
surface a client-side filter would add. The finish date is computed from recent
pace (`application/pace.py`) and shown with no setup; pinning it as a goal is
one POST, and a goal is a preference, so it works with review scheduling off.

**Every Start on these pages posts the track's name**, which is the one thing
they do that Browse does not: it is what makes the attempt's own page know
which track to offer the next step of (`interface/web/navigation.py`).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from fastapi import APIRouter, Form
from starlette.requests import Request  # noqa: TC002  (FastAPI reads this at runtime)
from starlette.responses import HTMLResponse, RedirectResponse, Response

from practice.application.pace import project, read_goal
from practice.application.preferences import clear_goal, goal_for, set_goal
from practice.application.tracks import filter_steps
from practice.interface.web.errors import render_problem

if TYPE_CHECKING:
    from fastapi.templating import Jinja2Templates

    from practice.application.dto import OpenAttempt
    from practice.application.tracks import TrackProgress
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

    def find(name: str) -> TrackProgress | None:
        return next(
            (
                progress
                for progress in services.follow_tracks()
                if progress.track.name == name
            ),
            None,
        )

    def no_such_track(request: Request, name: str) -> Response:
        return render_problem(
            templates,
            request,
            title="No such track",
            detail=f"This library has no track called {name!r}.",
            status=404,
        )

    @router.get("/tracks/{name}", response_class=HTMLResponse)
    def track(request: Request, name: str, q: str = "", show: str = "all") -> Response:
        found = find(name)
        if found is None:
            return no_such_track(request, name)
        today = services.clock.today()
        remaining = found.total - found.done
        days = found.first_pass_days
        target = goal_for(services.settings, name)
        return templates.TemplateResponse(
            request=request,
            name="track.html",
            context={
                "title": found.track.title,
                "progress": found,
                "open_by_exercise": _open_by_exercise(services),
                "steps": filter_steps(found, q, show),
                "q": q.strip(),
                "show": show if show in ("todo", "done") else "all",
                "projection": project(days, remaining, today),
                "goal": target,
                "goal_reading": (
                    read_goal(target, days, remaining, today) if target else None
                ),
                "today": today,
                "one_day": timedelta(days=1),
            },
        )

    @router.post("/tracks/{name}/goal")
    def set_track_goal(
        request: Request, name: str, target_on: str = Form("")
    ) -> Response:
        """Pin a finish-by date. Blank is "use the projection", which is the
        point of the button: the common case takes no typing. With neither a
        date nor enough history to project one, say so rather than guess.
        """
        found = find(name)
        if found is None:
            return no_such_track(request, name)
        today = services.clock.today()

        def refuse(detail: str) -> Response:
            return render_problem(
                templates, request, title="No goal set", detail=detail, status=422
            )

        if target_on.strip():
            try:
                chosen = date.fromisoformat(target_on.strip())
            except ValueError:
                return refuse("That is not a date; use the form YYYY-MM-DD.")
        else:
            projection = project(found.first_pass_days, found.total - found.done, today)
            if projection is None or projection.finish_on is None:
                return refuse(
                    "There is no pace to project from yet (or it is over a year "
                    "out). Pick a date yourself."
                )
            chosen = projection.finish_on
        if chosen <= today:
            return refuse("A goal has to be a day after today.")
        set_goal(services.settings, name, chosen)
        return RedirectResponse(f"/tracks/{name}", status_code=303)

    @router.post("/tracks/{name}/goal/clear")
    def clear_track_goal(request: Request, name: str) -> Response:
        if find(name) is None:
            return no_such_track(request, name)
        clear_goal(services.settings, name)
        return RedirectResponse(f"/tracks/{name}", status_code=303)

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
