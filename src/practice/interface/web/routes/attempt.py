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

**The tutor panel is drawn here and driven from `routes/tutor.py`**, a fourth
time and for no new reason: this module owns the page and formats the URL, and
the endpoint that hands an attempt back as text to paste into a chat lives
beside the others under it (Phase 18).

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
from practice.domain.errors import AttemptStateError, DomainError
from practice.domain.exercise import GitScenarioSpec, editable_source
from practice.domain.ids import AttemptId
from practice.interface.web.errors import render_problem
from practice.interface.web.navigation import known_track, next_context
from practice.interface.web.routes.console import COMMAND_URL, SCENARIO_SUBMIT_URL
from practice.interface.web.routes.editor import EDITOR_URL, WATCH_URL
from practice.interface.web.routes.review import REVIEW_URL
from practice.interface.web.routes.tutor import TUTOR_URL
from practice.interface.web.vendor import mode_file

if TYPE_CHECKING:
    from datetime import timedelta

    from fastapi.templating import Jinja2Templates

    from practice.composition import Services

__all__ = ["CURRENT_URL", "HINT_URL", "SUBMIT_URL", "build_router"]

#: Where the editor posts a solution. A template builds the attempt's own URL from
#: this, so the route and the page cannot disagree about the path.
SUBMIT_URL = "/api/attempt/{attempt_id}/submit"

#: Where the prompt panel asks for the next hint. No index in it, deliberately: an
#: endpoint taking one is an endpoint a solver skips to the last hint with, and the
#: progression is the thing being recorded.
HINT_URL = "/api/attempt/{attempt_id}/hint"

#: Where an open workbench reports that its tab has come to the front. A POST,
#: because it changes which attempt is current and a GET here "cannot change
#: anything" (`security.py`) -- which is also why loading the page does not do
#: it (ADR 0026).
CURRENT_URL = "/api/attempt/{attempt_id}/current"


def build_router(services: Services, templates: Jinja2Templates) -> APIRouter:
    """The workbench, closed over the services it reads."""
    router = APIRouter()

    @router.get("/attempt/{attempt_id}", response_class=HTMLResponse)
    def workbench(
        request: Request, attempt_id: str, track: str | None = None
    ) -> Response:
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
        # Two questions, and Phase 14 is where they stopped having one answer.
        # `editable` is *is there a file to edit* -- true for a kata and for a
        # SQL drill. `is_scenario` is *is there a console over a repository*.
        # Asking `isinstance(spec, KataSpec)` and using it for both was correct
        # for exactly as long as there were two kinds.
        editable = editable_source(spec)
        is_scenario = isinstance(spec, GitScenarioSpec)

        # **The clock is read here and not in `OpenWorkbench`**, which keeps
        # that use case's "no clock, this only reads" promise intact. How much
        # time is left is a reading of the attempt rather than part of it, the
        # attempt answers it given a `now`, and the surface drawing the page is
        # the thing that has one. A clock injected into the use case for a
        # display value would make every caller that does not want it pass one.
        now = services.clock.now()
        left = opened.attempt.remaining(now)
        # The track this attempt was started on, from the query string and
        # checked against the library. `None` for an attempt started from
        # Browse, and for a link kept past a track's rename.
        track_name = known_track(services, track)
        return templates.TemplateResponse(
            request=request,
            name="workbench.html",
            context={
                "title": opened.exercise.title,
                "workbench": opened,
                "is_kata": editable is not None,
                # The mode name CodeMirror knows this language by. From the spec
                # rather than hardcoded, so a second language is a content change
                # and a vendored mode file -- which is the whole claim of §15 Q3,
                # and the claim a third kind is the first real test of: `sql` is
                # a mode CodeMirror already has, so the drill workbench needed a
                # vendored file and no code.
                "editor_mode": editable.language if editable else None,
                # The vendored file that *defines* that mode, from the manifest
                # rather than built from the name here -- see the comment in
                # `workbench.html` and `vendor.mode_file`.
                "editor_mode_file": mode_file(editable.language if editable else None),
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
                "repo": services.inspect_repository(parsed) if is_scenario else None,
                # Only meaningful for an active kata, and the template only
                # draws the control for one -- formatted unconditionally for the
                # same reason the console's two URLs are, so that there is one
                # place a path can be got wrong.
                "editor_url": EDITOR_URL.format(attempt_id=parsed),
                "watch_url": WATCH_URL.format(attempt_id=parsed),
                "hint_url": HINT_URL.format(attempt_id=parsed),
                "current_url": CURRENT_URL.format(attempt_id=parsed),
                "review_url": REVIEW_URL.format(attempt_id=parsed),
                # Formatted unconditionally, like the rest. Whether the panel
                # that posts to it is drawn is the template's question, and it
                # asks the attempt's policy rather than anything decided here.
                "tutor_url": TUTOR_URL.format(attempt_id=parsed),
                # Only for a finished attempt, because `OfferReview` refuses one
                # with no verdict -- there is nothing to read a grade off. The
                # template asks the same question to decide which half of the
                # page to draw, so the two cannot disagree.
                "review": (None if opened.is_active else services.offer_review(parsed)),
                # Posted back by both submit forms, so the verdict fragment
                # can offer the step after this one on the same track.
                "track_name": track_name,
                # The block under a finished attempt's verdict. Only read then,
                # like `review`, and for the same reason both submit routes
                # build it too: a reload has to show what the submission showed.
                **(
                    {}
                    if opened.is_active
                    else next_context(services, opened.exercise.id, track_name)
                ),
                # Whole minutes, because the deadline is authored in minutes and
                # a seconds figure on a page that does not tick is a precision
                # the number does not have. Both directions are formatted so the
                # template never negates a timedelta.
                "now": now,
                "limit_minutes": _whole_minutes(opened.attempt.policy.deadline_seconds),
                "minutes_left": _minutes_left(left),
                "minutes_over": _minutes_over(-left if left is not None else None),
            },
        )

    # Six parameters, each a field of one form: FastAPI reads a route's inputs
    # off its signature, so the form *is* the parameter list and a parameter
    # object would be a model that exists to be unpacked by the framework.
    @router.post("/api/attempt/{attempt_id}/submit", response_class=HTMLResponse)
    def submit(  # noqa: PLR0913, PLR0917
        request: Request,
        attempt_id: str,
        source: Annotated[str, Form()],
        time: Annotated[str | None, Form()] = None,
        space: Annotated[str | None, Form()] = None,
        track: Annotated[str | None, Form()] = None,
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
                **next_context(
                    services,
                    submission.attempt.exercise_id,
                    known_track(services, track),
                ),
            },
        )

    @router.post(CURRENT_URL)
    def current(attempt_id: str) -> Response:
        """Make this the attempt a tutor is shown, because its tab is in front.

        No body either way: the page that sends this does not read the answer,
        and there is nothing on it to redraw. The status is still the honest
        one, for whoever is reading the server's log -- a tab left open across
        a submission goes on calling this about a finished attempt, and that
        is a 409 rather than a quiet success.
        """
        try:
            services.mark_current_attempt(AttemptId.parse(attempt_id))
        except AttemptStateError:
            return Response(status_code=409)
        except (ApplicationError, DomainError, ValueError):
            return Response(status_code=404)
        return Response(status_code=204)

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


def _whole_minutes(seconds: int | None) -> int | None:
    """A deadline in whole minutes, for the sentence that states the limit."""
    return None if seconds is None else seconds // 60


def _minutes_left(span: timedelta | None) -> int | None:
    """Time remaining in whole minutes, rounded *up*. `None` when untimed.

    Up, because a clock face rounds up: fourteen minutes and fifty-nine seconds
    reads as fifteen, and the page is drawn a second or two after the attempt
    was opened. Flooring would greet a fresh fifteen-minute interview with "14
    minutes left of 15" and, worse, would announce "0 minutes left" to somebody
    with fifty seconds in hand.
    """
    if span is None:
        return None
    return -(-int(span.total_seconds()) // 60)


def _minutes_over(span: timedelta | None) -> int | None:
    """Time past the deadline in whole minutes, rounded *down*.

    The opposite lean to `_minutes_left`, and for the same reason it is the safe
    one: two and a half minutes late should not be reported as three.
    """
    if span is None:
        return None
    return int(span.total_seconds()) // 60
