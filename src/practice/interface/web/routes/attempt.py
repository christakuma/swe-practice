"""`/attempt/{id}` — the workbench, and the kata submission that closes it.

Two routes and one page: the prompt on the left, and on the right either a kata
editor, a git scenario console (`routes/console.py`, whose endpoints drive it) or
the verdict, once the attempt is graded. **One page for both exercise kinds**, with
the branch in the template rather than in the URL: an attempt is an attempt, the
prompt, the hints, the id and the lifecycle are identical, and splitting the route
would have duplicated `OpenWorkbench`'s four error paths for the sake of a layout
difference.

This module keeps the kata submission because that is the one that carries a body
-- the editor's source and a complexity claim. A scenario sends nothing, which is
the argument `routes/console.py` makes for its own submit route.

**Own-editor mode is drawn here and driven from `routes/editor.py`**, which is
the third instance of the same division: this module owns the page, and the
module beside it owns the endpoints under it. Phase 10's addition, and the one
piece of the kata surface that is about something outside the browser.

**The schedule control is drawn here and driven from `routes/review.py`**, which
is the same division the console has: this module owns the page and the other
owns the endpoints under it. It is a separate module rather than a third route
here because both submit routes render the block -- a kata's and a scenario's --
and a constant living in either one of them would have to be imported by the
other, which is the import cycle `attempt` and `console` already avoid by
pointing one way.

**Hint reveal is here rather than in either half**, because hints belong to the
attempt and not to the exercise kind: a kata has them and a git scenario has them,
and the panel they appear in is in the shared prompt column. It is the one endpoint
on this page that is a GET-shaped idea and a POST in fact -- revealing a hint writes
an event the attempt records (§4.3), so it is not safe to repeat and must not be
something a browser can prefetch.

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
from practice.interface.web.routes.console import COMMAND_URL, SCENARIO_SUBMIT_URL
from practice.interface.web.routes.editor import EDITOR_URL
from practice.interface.web.routes.review import REVIEW_URL

if TYPE_CHECKING:
    from fastapi.templating import Jinja2Templates

    from practice.composition import Services

__all__ = ["HINT_URL", "SUBMIT_URL", "build_router"]

#: Where the editor posts a solution. A template builds the attempt's own URL from
#: this, so the route and the page cannot disagree about the path.
SUBMIT_URL = "/api/attempt/{attempt_id}/submit"

#: Where the prompt panel asks for the next hint. No index in it, deliberately: an
#: endpoint taking one is an endpoint a solver skips to the last hint with, and the
#: progression is the thing being recorded.
HINT_URL = "/api/attempt/{attempt_id}/hint"


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
        is_kata = isinstance(spec, KataSpec)
        return templates.TemplateResponse(
            request=request,
            name="workbench.html",
            context={
                "title": opened.exercise.title,
                "workbench": opened,
                "is_kata": is_kata,
                # The mode name CodeMirror knows this language by. From the spec
                # rather than hardcoded, so a second language is a content change
                # and a vendored mode file -- which is the whole claim of §15 Q3.
                "editor_mode": spec.language if isinstance(spec, KataSpec) else None,
                "submit_url": SUBMIT_URL.format(attempt_id=parsed),
                # Both console endpoints, formatted here for the same reason the
                # kata's is: the page builds every URL it posts to from the
                # constant the route is declared with, so the two cannot drift.
                "command_url": COMMAND_URL.format(attempt_id=parsed),
                "scenario_submit_url": SCENARIO_SUBMIT_URL.format(attempt_id=parsed),
                # Only for a scenario, and not because it is wasted on a kata:
                # `InspectRepository` *refuses* a kata, because a directory with a
                # stub in it is not a repository in a strange state, it is a
                # question that does not apply.
                "repo": None if is_kata else services.inspect_repository(parsed),
                # Only meaningful for an active kata, and the template only
                # draws the control for one -- formatted unconditionally for the
                # same reason the console's two URLs are, so that there is one
                # place a path can be got wrong.
                "editor_url": EDITOR_URL.format(attempt_id=parsed),
                "hint_url": HINT_URL.format(attempt_id=parsed),
                "review_url": REVIEW_URL.format(attempt_id=parsed),
                # Only for a finished attempt, because `OfferReview` refuses one
                # with no verdict -- there is nothing to read a grade off. The
                # template asks the same question to decide which half of the
                # page to draw, so the two cannot disagree.
                "review": (None if opened.is_active else services.offer_review(parsed)),
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
            name="partials/graded.html",
            context={
                "verdict": submission.verdict,
                # Read back through the use case rather than assembled from the
                # submission: the schedule block has to know whether a card
                # already exists for this exercise, and a submission has never
                # heard of one.
                "review": services.offer_review(parsed),
                "review_url": REVIEW_URL.format(attempt_id=parsed),
            },
        )

    @router.post(HINT_URL, response_class=HTMLResponse)
    def hint(request: Request, attempt_id: str) -> Response:
        """Reveal the next hint, append it, and re-render the counter out of band.

        The same two-part response shape the console uses, and for the same reason:
        one request changes two places on the page -- the list of hints and the
        "one left" note under the button -- and htmx swaps both from it.

        A refusal lands in the list rather than replacing the page, because the
        reader is looking at the list. The two it can be are *no hints left*, which
        the aggregate raises, and *this attempt is finished*, which it also raises;
        both are sentences written to be read, so neither is rephrased here.
        """
        try:
            parsed = AttemptId.parse(attempt_id)
            revealed = services.reveal_hint(parsed)
        except (ApplicationError, DomainError, ValueError) as exc:
            return templates.TemplateResponse(
                request=request,
                name="partials/hint-refusal.html",
                context={"detail": str(exc)},
            )

        return templates.TemplateResponse(
            request=request,
            name="partials/hint-response.html",
            context={
                "revealed": revealed,
                "attempt": revealed.attempt,
                # The status block holds the button, so it needs the URL it posts
                # to even when it is being re-rendered by a response from it.
                "hint_url": HINT_URL.format(attempt_id=parsed),
                "oob": True,
            },
        )

    return router


def _claim(time: str | None, space: str | None) -> ComplexityClaim | None:
    """Both axes or neither; see `submit`."""
    if not time or not space:
        return None
    return ComplexityClaim(time=time, space=space)
