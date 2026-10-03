"""The git scenario half of `/attempt/{id}`: a command console, and its submission.

A separate route module from `attempt.py` rather than two more endpoints on it, and
the split is the same one the application layer already made: `RunScenarioCommand`
and `SubmitScenario` are not variations on the kata pair, they are the other
exercise kind's whole surface. The workbench *page* is shared — one GET, one
template, one layout — and what it renders on the right is either an editor or this.

**A command is a POST that appends, never one that replaces.** `hx-swap="beforeend"`
into the transcript list, so the page accumulates what happened in the order it
happened. The alternative — re-render the whole console on every command — would be
one template fewer and would throw away the thing a console is *for*: a solver
reading back three commands to work out where the repository went sideways. It also
makes the scroll position jump on every keystroke's worth of work.

**The transcript is rebuilt from the attempt's event log on page load**, not held in
the browser. That is what makes a reload, a second tab and a resumed attempt from
yesterday all show the same console: `Attempt.commands` is the record, and this page
is a view of it. Phase 6's claim that an attempt outlives its process is what this
cashes in — `practice resume <id> --commands` and this console write into the same
log, and neither can tell which one came first.

**A refused command is an entry in the transcript, not an error page.** Bad syntax,
a program the exercise does not allow, an exhausted budget: all three are things the
solver just typed, and the place they need to be told is the line under what they
typed. §8.1's whole argument for rejecting `echo x > f` loudly is that the rejection
teaches — so it is rendered where the teaching lands, with the line it is about
echoed above it, which is also what makes `parse_command_line`'s deliberately
sentence-fragment messages ("is not a command") read correctly.

**The repository is re-read after every command, not patched.** The response
carries the appended entry and the whole repo state panel, and the panel is built
from a fresh `RepoQuery` — which is also why `InspectRepository` is called here
rather than the route assembling one itself: the panel a solver decides to submit
from reads the repository through the same port the grader will.

**Submitting a scenario is its own route with no body.** There is nothing to send:
the thing being graded is the repository on disk, and the log already holds every
command that put it there (`SubmitScenario` makes the same point about itself). A
`source` field made optional on the kata route would have been one endpoint and a
branch, and the branch would be *on exercise kind* inside an interface module — the
one dispatch the kind registry exists to own.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Form
from starlette.requests import Request  # noqa: TC002  (FastAPI reads this at runtime)
from starlette.responses import HTMLResponse, Response

from practice.application.errors import ApplicationError
from practice.domain.errors import DomainError
from practice.domain.ids import AttemptId
from practice.interface.web.routes.review import REVIEW_URL

if TYPE_CHECKING:
    from fastapi.templating import Jinja2Templates

    from practice.composition import Services

__all__ = ["COMMAND_URL", "SCENARIO_SUBMIT_URL", "build_router"]

#: Where the console posts a typed line, and where it posts a submission. The
#: templates build both from these, so a route and the page that drives it cannot
#: disagree about the path -- the same reason `SUBMIT_URL` is a constant.
COMMAND_URL = "/api/attempt/{attempt_id}/command"
SCENARIO_SUBMIT_URL = "/api/attempt/{attempt_id}/submit-scenario"


def build_router(services: Services, templates: Jinja2Templates) -> APIRouter:
    """The console, closed over the services it drives."""
    router = APIRouter()

    @router.post(COMMAND_URL, response_class=HTMLResponse)
    def command(
        request: Request, attempt_id: str, line: Annotated[str, Form()]
    ) -> Response:
        """Run one typed line and return the transcript entry it produced.

        Blocking, like every endpoint in this app: the line starts a `git` process
        in the attempt's workspace and waits up to the exercise's own timeout for
        it. Starlette runs a `def` endpoint in a threadpool, so that wait costs one
        thread rather than the event loop.

        A command that *fails* is not an error here. `git revert` hitting a
        conflict exits non-zero and is frequently the most instructive thing in an
        attempt, so the exit code and both streams go into the entry and the
        response is a 200 either way.
        """
        try:
            parsed = AttemptId.parse(attempt_id)
            ran = services.run_scenario_command(parsed, line)
        except (ApplicationError, DomainError, ValueError) as exc:
            return _refused(templates, request, line=line, detail=str(exc))

        return templates.TemplateResponse(
            request=request,
            name="partials/console-response.html",
            context={
                "command": ran.command,
                "attempt": ran.attempt,
                "repo": services.inspect_repository(parsed),
                # Everything in this response is swapped by id except the entry
                # itself, which is appended. One flag, read by both partials.
                "oob": True,
            },
        )

    @router.post(SCENARIO_SUBMIT_URL, response_class=HTMLResponse)
    def submit(request: Request, attempt_id: str) -> Response:
        """Grade the repository as the solver left it and return the verdict.

        No form body, by the module docstring's argument. The fragment is the same
        `partials/graded.html` the kata route returns and the page includes for a
        finished attempt, which is what makes a reload show what the submission
        showed -- the schedule control included, since scheduling belongs to the
        attempt and not to the exercise kind.
        """
        try:
            parsed = AttemptId.parse(attempt_id)
            submission = services.submit_scenario(parsed)
        except (ApplicationError, DomainError, ValueError) as exc:
            # A fragment at status 200, for the reason the kata route states: htmx
            # does not swap a 4xx by default, so a refusal sent as one vanishes,
            # which is the opposite of saying what went wrong.
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
                "review": services.offer_review(parsed),
                "review_url": REVIEW_URL.format(attempt_id=parsed),
            },
        )

    return router


def _refused(
    templates: Jinja2Templates, request: Request, *, line: str, detail: str
) -> Response:
    """A command that never ran, as a transcript entry.

    Status 200 and an entry rather than a 4xx and a page: see the module docstring.
    The line is echoed above the reason because the reason is often a fragment about
    it, and because a console that silently dropped a rejected line would leave
    someone retyping it.
    """
    return templates.TemplateResponse(
        request=request,
        name="partials/console-refusal.html",
        context={"line": line, "detail": detail},
        status_code=200,
    )
