"""`POST /api/attempt/{id}/review` — the one endpoint in Phase 9 that writes.

One route and one constant, and the constant is why it is a module of its own.
Three places render the schedule block — the workbench page, the kata submission
and the scenario submission — and the latter two live in `routes/attempt.py` and
`routes/console.py`, which already point one way: `attempt` imports `console`'s
URLs. A fourth constant in either of them would have to be imported by the other
and close the cycle. A third module both can point at costs one file and keeps
the import graph a tree, which is the property `app.py` claims for the whole
package.

**A POST, not a PUT**, even though one attempt may only review once. The write is
*record that this review happened*: it creates a card where there was none, moves
the interval, and is refused outright on a repeat — so nothing about it is
idempotent in the way a PUT promises. The refusal is the Phase 4 shape, one layer
out: `Attempt.complete` guards a second submission because the attempt is the
thing being written, and the aggregate cannot guard this one because the thing
being written is a card.

**The refusal renders into the schedule block rather than replacing the page.**
The reader pressed a button in that block and is looking at it, and the two
refusals it can produce — *already reviewed*, and *this attempt has no verdict* —
are both sentences written to be read, so neither is rephrased here. Status 200,
for the reason every fragment route in this app gives: htmx does not swap a 4xx
by default, so a refusal sent as one vanishes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Form
from starlette.requests import Request  # noqa: TC002  (FastAPI reads this at runtime)
from starlette.responses import HTMLResponse, Response

from practice.application.errors import ApplicationError
from practice.domain.errors import DomainError
from practice.domain.ids import AttemptId
from practice.domain.review import Grade

if TYPE_CHECKING:
    from fastapi.templating import Jinja2Templates

    from practice.composition import Services

__all__ = ["REVIEW_URL", "build_router"]

#: Where the schedule block posts a grade. The templates build the attempt's own
#: URL from this, so the route and the page cannot disagree about the path.
REVIEW_URL = "/api/attempt/{attempt_id}/review"


def build_router(services: Services, templates: Jinja2Templates) -> APIRouter:
    """The schedule control's endpoint, closed over the services it writes to."""
    router = APIRouter()

    @router.post(REVIEW_URL, response_class=HTMLResponse)
    def review(
        request: Request,
        attempt_id: str,
        grade: Annotated[str | None, Form()] = None,
    ) -> Response:
        """Move the card and redraw the schedule block.

        **An unreadable grade is dropped rather than refused**, which falls out of
        `grade=None` already meaning *apply the suggestion*. The only thing that
        posts here is a button built from the `Grade` enum, so a value that is not
        one of the four did not come from the page — and the honest answer to it
        is the tool's own reading rather than a 422 about a string nobody typed.
        `routes/browse.py` drops an unknown filter value for the same reason.

        Blocking, like every endpoint in this app, and the only one here that is
        genuinely cheap: two row reads and a write, no process started.
        """
        try:
            parsed = AttemptId.parse(attempt_id)
            reviewed = services.grade_review(parsed, _grade(grade))
        except (ApplicationError, DomainError, ValueError) as exc:
            return templates.TemplateResponse(
                request=request,
                name="partials/review.html",
                context={"detail": str(exc)},
            )

        return templates.TemplateResponse(
            request=request,
            name="partials/review.html",
            context={"reviewed": reviewed},
        )

    return router


def _grade(value: str | None) -> Grade | None:
    """One of the four, or `None` for "use the suggestion"; see `review`."""
    if value is None:
        return None
    try:
        return Grade(value)
    except ValueError:
        return None
