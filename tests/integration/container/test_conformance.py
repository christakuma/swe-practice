"""The fake and the real `BuildQuery` give the same verdicts on reachable states.

The fake is what the eleven assertions' unit tests run against, so it is only
evidence if it describes states the real parser can produce the way the parser
describes them. Each case states one state twice: as a Dockerfile or compose
file for the real query, and as answers for the fake. Then it requires every
assertion to report identically over both.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.container import ParsedBuildQuery
from practice.domain.containers import registry
from practice.domain.exercise import CheckSpec
from practice.domain.ports import PathAccess, PathEntry
from practice.domain.verdict import Severity
from tests.fakes import FakeBuildQuery
from tests.fakes.build import a_stage, an_account, exec_form, shell_form

if TYPE_CHECKING:
    from collections.abc import Mapping

SHELL = "(^|/)(ba|da)?sh$"

CHECKS = (
    ("base_image_matches", {"pattern": "-slim$"}),
    ("ordered_before", {"first": "^COPY requirements", "then": r"^COPY \. "}),
    ("pid1_matches", {"pattern": SHELL}),
    ("command_matches", {"pattern": "0.0.0.0:8000"}),
    ("runs_as", {"pattern": "^root$"}),
    ("instruction_matches", {"pattern": "^RUN pip"}),
    ("path_in_image", {"path": ".env"}),
    ("stage_count", {"at_least": 2}),
)

DOCKERFILE = (
    "FROM python:3.12-slim\n"
    "COPY requirements.txt .\n"
    "RUN pip install -r requirements.txt\n"
    "COPY . .\n"
    "USER app\n"
    "CMD gunicorn --bind 0.0.0.0:8000 app:app\n"
)

FAKE = FakeBuildQuery(
    stages=[
        a_stage(
            "python:3.12-slim",
            exec_form("COPY", "requirements.txt", ".", at=2),
            shell_form("RUN", "pip install -r requirements.txt", at=3),
            exec_form("COPY", ".", ".", at=4),
            exec_form("USER", "app", at=5),
            shell_form("CMD", "gunicorn --bind 0.0.0.0:8000 app:app", at=6),
        )
    ],
    process=["/bin/sh", "-c", "gunicorn --bind 0.0.0.0:8000 app:app"],
    user="app",
    in_image=[".env", "app.py", "requirements.txt"],
)


def spec(assertion: str, params: Mapping[str, str | int]) -> CheckSpec:
    return CheckSpec(
        id="a-check",
        label="A label.",
        severity=Severity.REQUIRED,
        assertion=assertion,
        params=params,
    )


@pytest.mark.parametrize(("assertion", "params"), CHECKS, ids=[c[0] for c in CHECKS])
def test_a_dockerfile_reads_the_same_through_both(
    assertion: str, params: dict[str, str | int]
) -> None:
    real = ParsedBuildQuery(
        context={".env": "", "app.py": "", "requirements.txt": ""},
        editable="Dockerfile",
        source=DOCKERFILE,
    )
    check = spec(assertion, params)
    assert registry.evaluate(check, real) == registry.evaluate(check, FAKE)


def test_a_compose_file_reads_the_same_through_both() -> None:
    real = ParsedBuildQuery(
        context={},
        editable="compose.yaml",
        source=(
            "services:\n  api:\n    depends_on: [db]\n"
            "    volumes: ['.:/app', /app/node_modules]\n"
            "  db:\n    image: x\n"
        ),
    )
    fake = FakeBuildQuery(
        services={
            "api": {
                "depends_on": {"db": {"condition": "service_started"}},
                "volumes": [
                    {"type": "bind", "source": ".", "target": "/app"},
                    {"type": "volume", "target": "/app/node_modules"},
                ],
            },
            "db": {"image": "x"},
        }
    )
    for assertion, params in (
        (
            "service_value",
            {"service": "api", "key": "depends_on.db.condition", "pattern": "started"},
        ),
        ("service_value", {"service": "db", "key": "healthcheck.test", "pattern": "."}),
        ("service_value", {"service": "web", "key": "image", "pattern": "."}),
        (
            "service_mount",
            {"service": "api", "target": "/app/node_modules", "type": "volume"},
        ),
        ("service_mount", {"service": "api", "target": "/app", "type": "volume"}),
        ("service_mount", {"service": "db", "target": "/app", "type": "bind"}),
    ):
        check = spec(assertion, params)
        assert registry.evaluate(check, real) == registry.evaluate(check, fake)


def test_ownership_reads_the_same_through_both() -> None:
    """`path_writable` over a directory `chown` gave away, and one it did not."""
    real = ParsedBuildQuery(
        context={"app.py": ""},
        editable="Dockerfile",
        source=(
            "FROM python:3.12-slim\n"
            "WORKDIR /app\n"
            "COPY . .\n"
            "RUN useradd -m app && mkdir -p data logs && chown app:app data\n"
            "USER app\n"
        ),
    )

    def entry(path: str, owner: str, uid: int, line: int) -> PathEntry:
        return PathEntry(
            path=path,
            uid=uid,
            gid=uid,
            mode=0o755,
            directory=True,
            owner=owner,
            line=line,
        )

    root, app = entry("/", "root:root", 0, 0), entry("/app", "root:root", 0, 2)
    fake = FakeBuildQuery(
        user="app",
        accounts=[an_account("app", 1000), an_account("nobody", 65534)],
        paths={
            "/app/data": PathAccess(
                chain=(root, app, entry("/app/data", "app:app", 1000, 4)),
                exists=True,
            ),
            "/app/logs": PathAccess(
                chain=(root, app, entry("/app/logs", "root:root", 0, 4)),
                exists=True,
            ),
            "/app/cache": PathAccess(chain=(root, app), exists=False),
        },
    )
    for params in (
        {"path": "/app/data"},
        {"path": "/app/logs"},
        {"path": "/app/cache"},
        {"path": "/app/data", "by": "nobody"},
        {"path": "/app/data", "by": "ghost"},
    ):
        check = spec("path_writable", params)
        assert registry.evaluate(check, real) == registry.evaluate(check, fake)
