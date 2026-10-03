"""`/browse` — the filterable exercise list, and the one place attempts begin.

**The filter is parsed here and matched in the domain.** `ExerciseFilter.matches`
is what decides, which is the same reason the in-memory fake delegates to it
rather than reimplementing the comparison: a second opinion about what a filter
means is how a browse page and a repository drift apart. What this module does is
the part that is genuinely the interface's job — turning three query strings into
the value object, and discarding a value that names nothing.

**An unknown filter value is dropped, not refused.** A query string is a thing
people edit by hand and share in links, and `?difficulty=medium&difficulty=hrad`
should show the mediums rather than a 422 about the typo. The alternative reads
as rigour and behaves as a dead end.

**Starting an attempt is a POST, and it redirects.** `POST /attempt` then `303`
to the workbench, so a reload of the workbench does not provision a second
workspace — the one bug a form-posting page gets for free if it renders its own
result. It is also the only mutating route in this phase that is not an HTMX
fragment, because what follows it is a different page rather than a piece of this
one.

PLAN.md §8.4 also lists *status* as a filter dimension, and it is still not here
after Phase 9 built the progress model it was waiting for. The reason changed
rather than went away: status is a property of *attempts and cards*, so an
`ExerciseFilter` carrying it would be a domain value object the content
repository cannot answer — the filtering would have to happen in this route,
after the query, which is the one thing this module's first paragraph says it
does not do. The two questions the dimension was for are both answered better
elsewhere: *what should I do now* is the dashboard's due queue, and *where am I
losing it* is `/progress`. What this page says without inventing anything is
which exercises have an attempt still open, as a **Resume** link.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Form, Query
from starlette.requests import Request  # noqa: TC002  (FastAPI reads this at runtime)
from starlette.responses import HTMLResponse, RedirectResponse, Response

from practice.application.errors import ApplicationError
from practice.domain.exercise import Difficulty, ExerciseFilter, ExerciseKind
from practice.domain.ids import ExerciseId, tag
from practice.interface.web.errors import render_problem

if TYPE_CHECKING:
    from collections.abc import Iterable

    from fastapi.templating import Jinja2Templates

    from practice.composition import Services
    from practice.domain.exercise import Exercise
    from practice.domain.ids import Tag

__all__ = ["build_router"]


def build_router(services: Services, templates: Jinja2Templates) -> APIRouter:
    """The library listing and the form that opens an attempt at one of them."""
    router = APIRouter()

    @router.get("/browse", response_class=HTMLResponse)
    def browse(
        request: Request,
        kind: Annotated[list[str] | None, Query()] = None,
        difficulty: Annotated[list[str] | None, Query()] = None,
        tags: Annotated[list[str] | None, Query()] = None,
    ) -> Response:
        """`None` rather than `[]` as the default, which is not a style choice.

        A mutable default is shared across calls, and FastAPI reads the default
        from the signature at import time — so the list it would hand every
        request is one object. `None` folded to `()` here costs a line and cannot
        be the bug.
        """
        criteria = _criteria(
            kinds=kind or (), difficulties=difficulty or (), tags=tags or ()
        )
        exercises = services.content.list_exercises(criteria)
        # One listing for the whole page rather than a lookup per row: the
        # question "is there an open attempt at this?" is answered for every
        # exercise at once, and `ListOpenAttempts` already makes the join.
        open_by_exercise = {
            open_attempt.attempt.exercise_id: open_attempt
            for open_attempt in services.list_open_attempts()
            if open_attempt.can_resume
        }
        return templates.TemplateResponse(
            request=request,
            name="browse.html",
            context={
                "title": "Browse",
                "exercises": exercises,
                "open_by_exercise": open_by_exercise,
                "selected": {
                    "kinds": set(criteria.kinds),
                    "difficulties": set(criteria.difficulties),
                    "tags": set(criteria.tags),
                },
                "all_kinds": list(ExerciseKind),
                "all_difficulties": list(Difficulty),
                "all_tags": _tags_in(services.content.list_exercises()),
            },
        )

    @router.post("/attempt")
    def start(request: Request, exercise_id: Annotated[str, Form()]) -> Response:
        """Provision a workspace and send the browser to the workbench.

        `303`, not `302`: the browser must follow it with a `GET` whatever it
        posted, and that is the whole point of the redirect — a workbench that
        rendered itself from the POST would provision a second workspace on every
        reload.
        """
        try:
            started = services.start_attempt(ExerciseId(exercise_id))
        except (ApplicationError, ValueError) as exc:
            return render_problem(
                templates, request, title="Cannot start", detail=str(exc), status=404
            )
        return RedirectResponse(f"/attempt/{started.attempt.id}", status_code=303)

    return router


def _criteria(
    *, kinds: Iterable[str], difficulties: Iterable[str], tags: Iterable[str]
) -> ExerciseFilter:
    """Query strings into the domain's own filter, dropping what it cannot read.

    An empty set means "no constraint on this dimension", which is what makes a
    dropped value behave the way a reader expects: a typo in one of three
    parameters narrows by the other two instead of erroring about the third.
    """
    return ExerciseFilter(
        kinds=frozenset(_members(ExerciseKind, kinds)),
        difficulties=frozenset(_members(Difficulty, difficulties)),
        tags=frozenset(_as_tags(tags)),
    )


def _members[T: (ExerciseKind, Difficulty)](
    enum: type[T], values: Iterable[str]
) -> Iterable[T]:
    """Every value that names a member. Both enums are `StrEnum`, so this is
    the same lookup the content loader gets for free from the YAML.
    """
    for value in values:
        try:
            yield enum(value)
        except ValueError:
            continue


def _as_tags(values: Iterable[str]) -> Iterable[Tag]:
    """`tag()` normalises and validates; anything it rejects is dropped."""
    for value in values:
        try:
            yield tag(value)
        except ValueError:
            continue


def _tags_in(exercises: Iterable[Exercise]) -> list[Tag]:
    """Every tag the library uses, sorted, for the filter control.

    Derived rather than configured: a tag list someone has to maintain is a tag
    list that will disagree with the content, and `practice validate` has no rule
    that would catch it.
    """
    found: set[Tag] = set()
    for exercise in exercises:
        found.update(exercise.tags)
    return sorted(found)
