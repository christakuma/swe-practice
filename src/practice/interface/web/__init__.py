"""The web app: FastAPI, Jinja2, HTMX, and four vendored files.

The real interface, in the sense PLAN.md §2 means it — commit graphs, diffs and
syntax-highlighted code are genuinely painful in a terminal. The Typer CLI remains
the second driving adapter over the same use cases, which is what makes the
hexagonal boundary evidence rather than decoration.

What is re-exported here is the factory and the asset manifest, nothing else. A
caller builds the app with `create_app(services)` and the composition root decides
what `services` is; route modules are reached through the app and never imported
from outside this package.
"""

from __future__ import annotations

from practice.interface.web.app import create_app
from practice.interface.web.vendor import ASSETS, VendoredAsset, static_root

__all__ = ["ASSETS", "VendoredAsset", "create_app", "static_root"]
