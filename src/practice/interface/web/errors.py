"""Turning an application error into a page, in one place.

Every route that can fail fails the same four ways — nothing has that id, the
exercise left the library, the workspace is gone, nothing can grade that kind —
because those are the four `application/errors.py` declares, and that file's own
argument is that *"every driving adapter maps them to something (an exit status, a
status code)"*. The CLI maps them to exit 2; this maps them to a status and a
page.

**A refusal is a page, not a traceback and not a JSON body.** The person reading
it is in a browser, mid-attempt, and the useful thing is the sentence the error
already carries — these messages are written to be read (`abandon it and start
again`), so the page's job is to show one rather than to compose a new one.

**Status codes, and why `404` for three different things.** An attempt that does
not exist, an exercise that has left the library, and a workspace that has been
collected are all *this URL no longer names anything you can work on*. Splitting
them across codes would be precision about the wrong thing: the reader needs the
sentence, and nothing automated consumes these pages — there is no API
(`openapi_url=None`), so the code is for the browser's history and nothing else.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.templating import Jinja2Templates
    from starlette.requests import Request
    from starlette.responses import Response

__all__ = ["render_problem"]


def render_problem(
    templates: Jinja2Templates,
    request: Request,
    *,
    title: str,
    detail: str,
    status: int,
) -> Response:
    """One refusal, rendered into the normal layout.

    The layout rather than a bare page, deliberately: a refusal is a place
    somebody needs to navigate *away* from, and a page without the header has
    taken the navigation away at the moment it is wanted.
    """
    return templates.TemplateResponse(
        request=request,
        name="problem.html",
        context={"title": title, "problem": title, "detail": detail},
        status_code=status,
    )
