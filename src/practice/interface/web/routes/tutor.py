"""`POST /api/attempt/{id}/context` — the attempt, as text to paste into a chat.

One route and one constant, in a module of its own for the reason `review.py`
gives: the workbench page formats this URL, and a constant living in
`attempt.py` would be one more thing that module owns about an endpoint it does
not serve. Phase 18; ADR 0023.

**A POST that writes nothing, and it is a POST because of what it carries.**
Every other read in this app is a GET. This one has a body: a kata's solution
lives in the browser's editor until it is submitted, and the textarea under
CodeMirror stops tracking it the moment the editor loads (`workbench.html`), so
the only way the server learns what the solver has typed is to be sent it. A
tutor shown the untouched stub while the solver looks at forty lines of their
own code would be answering a different question.

It also means the same-origin guard applies, which a GET would not have had —
and that is the right side to land on. The response is a transcript of what
somebody ran on their own machine, and `SameOriginMiddleware` already argues
that another page in the same browser should not be able to ask for one.

**Nothing is recorded**, which is the difference from the hint endpoint beside
it in the prompt column. Revealing a hint is something the tool did and can
vouch for; copying this is not evidence it was ever pasted anywhere, so the
attempt's log does not claim it was.

**The fragment is a textarea, not rendered Markdown.** The reader is going to
copy it, so what they need is the exact text — and a `<textarea>` is the one
element whose content the browser will select and copy byte for byte, with
autoescaping doing the right thing on the way in for free.

A refusal is a fragment in the same slot, at status 200, like every fragment
route here: htmx does not swap a 4xx, so a refusal sent as one would vanish. The
only one a solver should ever see is the interview's, and the workbench does not
draw the button for an open interview in the first place.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Form
from starlette.requests import Request  # noqa: TC002  (FastAPI reads this at runtime)
from starlette.responses import HTMLResponse, Response

from practice.application.errors import ApplicationError
from practice.application.tutor import render_markdown
from practice.domain.errors import DomainError
from practice.domain.ids import AttemptId

if TYPE_CHECKING:
    from fastapi.templating import Jinja2Templates

    from practice.composition import Services

__all__ = ["TUTOR_URL", "build_router"]

#: Where the workbench asks for the bundle. The page builds the attempt's own
#: URL from this, so the route and the button cannot disagree about the path.
TUTOR_URL = "/api/attempt/{attempt_id}/context"


def build_router(services: Services, templates: Jinja2Templates) -> APIRouter:
    """The tutor context's endpoint, closed over the services it reads."""
    router = APIRouter()

    @router.post(TUTOR_URL, response_class=HTMLResponse)
    def context(
        request: Request,
        attempt_id: str,
        source: Annotated[str | None, Form()] = None,
    ) -> Response:
        """Render the attempt for a tutor and return it as a fragment.

        `source` is the editor's contents, and absent for a git scenario, which
        has no editor. Absent rather than empty is a distinction the use case
        reads: `None` means "I am not holding a draft, use the file", and an
        empty string would mean the solver has deleted everything.
        """
        try:
            parsed = AttemptId.parse(attempt_id)
            bundle = services.export_tutor_context(parsed, draft=source)
        except (ApplicationError, DomainError, ValueError) as exc:
            return templates.TemplateResponse(
                request=request,
                name="partials/refusal.html",
                context={"detail": str(exc)},
            )

        return templates.TemplateResponse(
            request=request,
            name="partials/tutor-bundle.html",
            context={"bundle": render_markdown(bundle)},
        )

    return router
