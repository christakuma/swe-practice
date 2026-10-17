"""The orders service: one WSGI callable, served by gunicorn.

No framework, on purpose -- gunicorn serves any WSGI callable, and the exercise
is about the container, not the app.
"""

import json
import os
from collections.abc import Callable


def app(
    environ: dict[str, object], start_response: Callable[..., object]
) -> list[bytes]:
    if environ["PATH_INFO"] == "/health":
        body = b"ok\n"
        content_type = "text/plain"
    else:
        payload = {"service": "orders", "version": os.environ.get("APP_VERSION", "dev")}
        body = json.dumps(payload).encode() + b"\n"
        content_type = "application/json"
    start_response(
        "200 OK",
        [("Content-Type", content_type), ("Content-Length", str(len(body)))],
    )
    return [body]
