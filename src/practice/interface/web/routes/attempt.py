"""`/attempt/{id}` — the workbench.

One route in this phase and one page with two halves: the prompt on the left, the
editor on the right for a kata, and the verdict in place of the editor once the
attempt is graded. The git scenario half of this page — a command console, a repo
state panel and a commit graph — is Phase 8, and the page says so rather than
rendering an editor over a repository.

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

from typing import TYPE_CHECKING

from fastapi import APIRouter
from starlette.requests import Request  # noqa: TC002  (FastAPI reads this at runtime)
from starlette.responses import HTMLResponse, Response

from practice.application.errors import ApplicationError
from practice.domain.errors import DomainError
from practice.domain.exercise import KataSpec
from practice.domain.ids import AttemptId
from practice.interface.web.errors import render_problem

if TYPE_CHECKING:
    from fastapi.templating import Jinja2Templates

    from practice.composition import Services

__all__ = ["build_router"]


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
            },
        )

    return router
