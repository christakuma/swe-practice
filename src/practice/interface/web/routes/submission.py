"""What a submission returns, and `POST /api/attempt/{id}/concede` -- ADR 0029.

**One function decides which fragment a graded submission gets**, and three
routes call it: the kata's submit, the scenario's submit, and the concede
endpoint below. Before ADR 0029 the first two returned `partials/graded.html`
unconditionally, because a graded attempt was a finished one. Now a failure
leaves the attempt open and wants a different fragment -- the verdict, *still
open*, and a way to stop -- and a choice made in each route would be three
copies of an `if` that has to agree with the page's own (`workbench.html`
draws the same fragment for an open attempt that has failed before).

**A module of its own for the reason `review.py` gives**, sharpened: both
submit routes need this, and `console.py` cannot import from `attempt.py`,
which already imports `console.py`'s URLs. Living here keeps the import graph
pointing one way.

**Conceding is a POST that closes the attempt**, so it is not idempotent and
does not pretend to be: a second one is refused by the aggregate, in its own
words, into the same slot -- the submit routes' rule, for their reason.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Form
from starlette.requests import Request  # noqa: TC002  (FastAPI reads this at runtime)
from starlette.responses import HTMLResponse, Response

from practice.application.errors import ApplicationError
from practice.domain.errors import DomainError
from practice.domain.ids import AttemptId
from practice.interface.web.navigation import known_track, next_context
from practice.interface.web.routes.review import REVIEW_URL

if TYPE_CHECKING:
    from fastapi.templating import Jinja2Templates

    from practice.application.dto import Submission
    from practice.composition import Services

__all__ = ["CONCEDE_URL", "build_router", "render_submission"]

#: Where the failed-submission fragment posts to stop. The page and both
#: submit routes format it from this, so none of them can name another path.
CONCEDE_URL = "/api/attempt/{attempt_id}/concede"


def render_submission(
    services: Services,
    templates: Jinja2Templates,
    request: Request,
    submission: Submission,
    track: str | None,
) -> Response:
    """`partials/graded.html` if the attempt closed, `partials/failed.html` if not."""
    attempt_id = submission.attempt.id
    track_name = known_track(services, track)
    if not submission.closed:
        return templates.TemplateResponse(
            request=request,
            name="partials/failed.html",
            context={
                "verdict": submission.verdict,
                "tries": submission.tries,
                "concede_url": CONCEDE_URL.format(attempt_id=attempt_id),
                "track_name": track_name,
            },
        )
    return templates.TemplateResponse(
        request=request,
        name="partials/graded.html",
        context={
            "verdict": submission.verdict,
            # Read back through the use case rather than assembled from the
            # submission: the schedule block has to know whether a card already
            # exists for this exercise, and a submission has never heard of one.
            "review": services.offer_review(attempt_id),
            "review_url": REVIEW_URL.format(attempt_id=attempt_id),
            **next_context(services, submission.attempt.exercise_id, track_name),
        },
    )


def build_router(services: Services, templates: Jinja2Templates) -> APIRouter:
    """The concede endpoint, closed over the services it drives."""
    router = APIRouter()

    @router.post(CONCEDE_URL, response_class=HTMLResponse)
    def concede(
        request: Request,
        attempt_id: str,
        track: Annotated[str | None, Form()] = None,
    ) -> Response:
        """Close the attempt on its last failure and return the finished fragment."""
        try:
            submission = services.concede_attempt(AttemptId.parse(attempt_id))
        except (ApplicationError, DomainError, ValueError) as exc:
            return templates.TemplateResponse(
                request=request,
                name="partials/refusal.html",
                context={"detail": str(exc)},
            )
        return render_submission(services, templates, request, submission, track)

    return router
