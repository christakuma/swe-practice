"""One module per page, each exposing a `build_router(services, templates)`.

A package rather than one long `routes.py`, for the reason the CLI is one long
module and this is not: a Typer command is a function and a page is a function
plus a template plus a handful of decisions about what the template is handed, so
the unit that wants to be read together is bigger. Splitting on the page is also
what keeps `app.py` a list of what the app serves.

Nothing here imports `app.py`. The dependency runs one way — `app.py` calls each
`build_router` — which is what stops the circular import the decorator-on-import
style invites.
"""

from __future__ import annotations

__all__: list[str] = []
