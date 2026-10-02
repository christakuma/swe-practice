"""`/attempt/{id}` — the workbench, and the submission that closes it.

Two routes and one page: the prompt on the left, the editor on the right for a
kata, and the verdict in place of the editor once the attempt is graded. The git
scenario half of this page — a command console, a repo state panel and a commit
graph — is Phase 8, and the page says so rather than rendering an editor over a
repository.

**The submission returns HTML, not JSON**, which is PLAN.md §8.4's rule and the
whole shape of the HTMX bet (ADR 0007): the server renders the fragment and the
browser swaps it in, so there is one template for a verdict and no client-side
model of what a check is. `partials/verdict.html` is the same file the page
includes when it loads a finished attempt, which is what makes a reload show
exactly what the submission showed.

**It is a POST that completes the attempt, so it is not idempotent and does not
pretend to be.** A second submission is refused by the aggregate — `Attempt` has
guarded that since Phase 4 — and the refusal is rendered as a fragment into the
same slot, because the person who double-clicked Submit is looking at that slot
and nowhere else.

**The id in the URL is the full uuid.** That is the trade §11 named when it
refused `find_by_prefix` on the `AttemptRepository` port: *"the web app, where the
id is in a link nobody types."* A route that accepted a prefix would be re-adding
the port method for the ergonomics of a thing nobody types.

**A malformed id is a 404, not a 422.** `AttemptId.parse` raises on anything that
is not a uuid, and FastAPI would turn a `UUID`-typed path parameter into a
validation error page about the shape of the string. The reader of `/attempt/oops`
wants to be told there is nothing there.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Form
from starlette.requests import Request  # noqa: TC002  (FastAPI reads this at runtime)
from starlette.responses import HTMLResponse, Response

from practice.application.errors import ApplicationError
from practice.domain.attempt import ComplexityClaim
from practice.domain.errors import DomainError
from practice.domain.exercise import KataSpec
from practice.domain.ids import AttemptId
from practice.interface.web.errors import render_problem

if TYPE_CHECKING:
    from fastapi.templating import Jinja2Templates

    from practice.composition import Services

__all__ = ["SUBMIT_URL", "build_router"]

#: Where the editor posts a solution. A template builds the attempt's own URL from
#: this, so the route and the page cannot disagree about the path.
SUBMIT_URL = "/api/attempt/{attempt_id}/submit"


def build_router(services: Services, templates: Jinja2Templates) -> APIRouter:
    """The workbench, closed over the services it reads."""
    router = APIRouter()

    @router.get("/attempt/{attempt_id}", response_class=HTMLResponse)
    def workbench(request: Request, attempt_id: str) -> Response:
        try:
            parsed = AttemptId.parse(attempt_id)
            opened = services.open_workbench(parsed)
        except (ApplicationError, DomainError, ValueError) as exc:
            return render_problem(
                templates,
                request,
                title="Nothing to work on here",
                detail=str(exc),
                status=404,
            )

        spec = opened.exercise.spec
        return templates.TemplateResponse(
            request=request,
            name="workbench.html",
            context={
                "title": opened.exercise.title,
                "workbench": opened,
                "is_kata": isinstance(spec, KataSpec),
                # The mode name CodeMirror knows this language by. From the spec
                # rather than hardcoded, so a second language is a content change
                # and a vendored mode file -- which is the whole claim of §15 Q3.
                "editor_mode": spec.language if isinstance(spec, KataSpec) else None,
                "submit_url": SUBMIT_URL.format(attempt_id=parsed),
            },
        )

    @router.post("/api/attempt/{attempt_id}/submit", response_class=HTMLResponse)
    def submit(
        request: Request,
        attempt_id: str,
        source: Annotated[str, Form()],
        time: Annotated[str | None, Form()] = None,
        space: Annotated[str | None, Form()] = None,
    ) -> Response:
        """Grade the editor's contents and return the verdict as a fragment.

        **Both complexity axes or neither**, the same rule the CLI enforces and
        for the same reason: a `ComplexityClaim` refuses to hold one axis, because
        a claim about time alone cannot disagree with an expectation that has two
        (§4.3). Half a pair is dropped here rather than refused — the form is the
        only thing that sends them and sending one is not something a solver can
        do by hand.

        Blocking, like every endpoint in this app. Grading a kata starts a pytest
        subprocess and waits up to the exercise's time limit for it; Starlette
        runs a `def` endpoint in a threadpool, so that wait does not block the
        event loop. An `async def` here would stall the whole server for ten
        seconds on a failing solution.
        """
        try:
            parsed = AttemptId.parse(attempt_id)
            submission = services.submit_solution(
                parsed, source, complexity=_claim(time, space)
            )
        except (ApplicationError, DomainError, ValueError) as exc:
            # A fragment, not a page: the reader is looking at the slot under the
            # editor, and swapping a whole error page into it would be worse than
            # the error. The status is 200 for the same reason -- htmx does not
            # swap a 4xx response by default, so a refusal sent as one would
            # vanish, which is the opposite of telling someone what went wrong.
            return templates.TemplateResponse(
                request=request,
                name="partials/refusal.html",
                context={"detail": str(exc)},
            )

        return templates.TemplateResponse(
            request=request,
            name="partials/verdict.html",
            context={"verdict": submission.verdict},
        )

    return router


def _claim(time: str | None, space: str | None) -> ComplexityClaim | None:
    """Both axes or neither; see `submit`."""
    if not time or not space:
        return None
    return ComplexityClaim(time=time, space=space)
