"""The fake and the real `BuildQuery` give the same verdicts on reachable states.

The fake is what the eight assertions' unit tests run against, so it is only
evidence if it describes states the real parser can produce the way the parser
describes them. Each case states one state twice: as a Dockerfile or compose
file for the real query, and as answers for the fake. Then it requires every
assertion to report identically over both.
"""

from __future__ import annotations

import pytest

from practice.adapters.container import ParsedBuildQuery
from practice.domain.containers import registry
from practice.domain.exercise import CheckSpec
from practice.domain.verdict import Severity
from tests.fakes import FakeBuildQuery
from tests.fakes.build import a_stage, exec_form, shell_form

SHELL = "(^|/)(ba|da)?sh$"

CHECKS = (
    ("base_image_matches", {"pattern": "-slim$"}),
    ("ordered_before", {"first": "^COPY requirements", "then": r"^COPY \. "}),
    ("pid1_matches", {"pattern": SHELL}),
    ("command_matches", {"pattern": "0.0.0.0:8000"}),
    ("runs_as", {"pattern": "^root$"}),
    ("instruction_matches", {"pattern": "^RUN pip"}),
    ("path_in_image", {"path": ".env"}),
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


def spec(assertion: str, params: dict[str, str]) -> CheckSpec:
    return CheckSpec(
        id="a-check",
        label="A label.",
        severity=Severity.REQUIRED,
        assertion=assertion,
        params=params,
    )


@pytest.mark.parametrize(("assertion", "params"), CHECKS, ids=[c[0] for c in CHECKS])
def test_a_dockerfile_reads_the_same_through_both(
    assertion: str, params: dict[str, str]
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
        source="services:\n  api:\n    depends_on: [db]\n  db:\n    image: x\n",
    )
    fake = FakeBuildQuery(
        services={
            "api": {"depends_on": {"db": {"condition": "service_started"}}},
            "db": {"image": "x"},
        }
    )
    for params in (
        {"service": "api", "key": "depends_on.db.condition", "pattern": "started"},
        {"service": "db", "key": "healthcheck.test", "pattern": "."},
        {"service": "web", "key": "image", "pattern": "."},
    ):
        check = spec("service_value", params)
        assert registry.evaluate(check, real) == registry.evaluate(check, fake)
