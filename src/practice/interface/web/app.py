"""The FastAPI app, assembled from services that are handed to it.

**`create_app(services)` takes the object graph rather than building one**, which
is the same rule `composition.py` states for the whole project: there is exactly
one place that decides which adapters are real, and it is not here. A module-level
`app = FastAPI()` reading a global would make the web adapter a second wiring
point, and would make every test either monkeypatch that global or provision real
directories.

**Routers are built by function, not discovered.** Each route module exposes a
`build_router(services, templates)` and this file calls it. The alternative —
decorators evaluated on module import, reaching for the services through
`app.state` — is how most FastAPI examples are written and it inverts the
dependency: the route module would then import the app that imports it. Manual
injection keeps the import graph a tree and keeps `Services` visible in every
signature that holds one.

**One template environment, built here.** Autoescaping is on, which is
load-bearing rather than hygiene: a verdict's `actual` field carries captured
`stderr` from a command the solver wrote, so untrusted text reaches a template on
the normal path and not the exotic one.

**`grades` is a Jinja global, built from the enum.** The schedule block draws one
button per `Grade`, and four strings written into the template would be four
strings to miss if a fifth bucket is ever added -- the enum is the list, so the
template reads it rather than restating it.

**Two filters, registered rather than reimplemented.** `short_ref` turns
`refs/heads/main` into `main` for the repo state panel, and it is the application
layer's function rather than a copy in Jinja: the prefix list it strips is the same
one `RepoView.head_branch` uses, and two copies of it would be two places for
`feature/parser` to come out as `parser`. `commit_graph` renders a laid-out graph
as inline SVG and returns `Markup`, so no template needs `| safe` -- the escaping
decision stays in the module that does the escaping. `activity_chart` and
`mastery_chart` joined them in Phase 9 on the same terms, which is the whole of
what §8.4's "hand-rolled inline SVG generated in Python" costs: two filters and
no dependency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from practice.application.dto import short_ref
from practice.domain.review import Grade
from practice.interface.web.charts import render_activity, render_mastery
from practice.interface.web.commit_graph import render_graph
from practice.interface.web.routes import (
    attempt,
    browse,
    console,
    dashboard,
    editor,
    progress,
    review,
)
from practice.interface.web.security import SameOriginMiddleware
from practice.interface.web.vendor import static_root

if TYPE_CHECKING:
    from pathlib import Path

    from practice.composition import Services

__all__ = ["STATIC_URL", "create_app", "templates_root"]

#: Where `static/` is mounted, and the prefix the templates build asset links
#: from. Injected as a Jinja global rather than reached through `url_for`, which
#: is the finding from writing the offline test: **Starlette's `url_for` renders
#: an *absolute* URL**, so a layout written the documented way serves
#: `http://127.0.0.1/static/app.css` on every page. Harmless in effect -- it is
#: the request's own origin -- and wrong in two ways that matter here: the grep in
#: `tests/web/test_offline.py` cannot tell that `http://` from a CDN's, and a page
#: that hardcodes the host it was rendered for is a page that stops working the
#: moment it is saved, proxied or opened from the other loopback spelling.
STATIC_URL: Final = "/static"


def templates_root() -> Path:
    """The Jinja2 search path that ships inside this package.

    From `__file__`, like `static_root`, so the server finds its own templates
    from whatever directory it was started in.
    """
    return static_root().parent / "templates"


def create_app(services: Services) -> FastAPI:
    """Build the app over an already-wired object graph.

    `openapi_url=None` takes the interactive docs with it, and that is deliberate.
    They are a second surface that can POST to every route, and this app's routes
    start processes; there is also no API to explore, because HTMX fragments
    return HTML rather than JSON (PLAN.md §8.4). A liability with no matching use.
    """
    app = FastAPI(title="swe-practice", openapi_url=None)
    app.add_middleware(SameOriginMiddleware)
    app.mount(STATIC_URL, StaticFiles(directory=static_root()), name="static")

    templates = Jinja2Templates(directory=templates_root())
    templates.env.globals["static"] = STATIC_URL
    templates.env.globals["grades"] = tuple(Grade)
    templates.env.filters["short_ref"] = short_ref
    templates.env.filters["commit_graph"] = render_graph
    templates.env.filters["activity_chart"] = render_activity
    templates.env.filters["mastery_chart"] = render_mastery
    app.include_router(dashboard.build_router(services, templates))
    app.include_router(browse.build_router(services, templates))
    app.include_router(progress.build_router(services, templates))
    app.include_router(attempt.build_router(services, templates))
    # After `attempt`, which owns the page these endpoints drive. Order is not
    # load-bearing -- no two routers declare the same path -- but reading the
    # list top to bottom should follow a visitor: dashboard, browse, progress,
    # workbench, and then the console, the editor and the schedule inside it.
    app.include_router(console.build_router(services, templates))
    # Beside the console, and for the same reason: the other half of the kata's
    # surface, whose endpoints live under the page `attempt` owns.
    app.include_router(editor.build_router(services, templates))
    # Last, and after both: it is the endpoint under the fragment they return.
    app.include_router(review.build_router(services, templates))
    return app
