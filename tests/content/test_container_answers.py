"""Right answers the references do not use, each graded against its exercise.

CLAUDE.md's rule for content, *write the answer the prompt rules out, and run
that too*, has a twin that matters more to a grader: **write the answers the
prompt does not rule out, and check that none of them fails.** A solver cannot
tell *my answer is wrong* from *the grader is wrong*, so failing a correct
answer is the one mistake a grader must not make. Phase 22 found four such
places by doing this by hand (ADR 0030). Phase 23 keeps them here, where the
suite runs them, and `tests/docker/` builds the same
files on a real daemon to show each one really works.

Each case names the checks it is allowed to fail, which is only ever an
advisory: a reasonable answer that the exercise nudges towards a better one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import pytest

from practice.adapters.container import (
    DEFINITION_CHECK_ID,
    ParsedBuildQuery,
    context_files,
    grade_query,
)
from practice.adapters.content import load_exercise
from practice.config import content_root
from practice.domain.exercise import ContainerSpec
from practice.domain.verdict import Severity

if TYPE_CHECKING:
    from practice.domain.verdict import Verdict

DOCKER = content_root() / "docker"
COMPILER: Final = "the-image-ships-its-compiler"
MODULES: Final = "node-modules-vanished"
NON_ROOT: Final = "unable-to-open-database-file"

_BUILD = (
    "FROM golang:1.23 AS build\n"
    "WORKDIR /src\n"
    "COPY . .\n"
    "RUN CGO_ENABLED=0 go build -o /out/shortlink .\n"
)

_SLIM = "FROM python:3.12-slim\n"
_SERVE = 'CMD ["python", "app.py"]\n'

#: name -> (exercise, answer, the advisories it may fail)
ANSWERS: Final[dict[str, tuple[str, str, frozenset[str]]]] = {
    "distroless-final-stage": (
        COMPILER,
        (
            _BUILD + "FROM gcr.io/distroless/static-debian12:nonroot\n"
            "COPY --from=build /out/shortlink /shortlink\n"
            'ENTRYPOINT ["/shortlink"]\n'
        ),
        frozenset(),
    ),
    "same-path-and-cmd-as-the-stub": (
        COMPILER,
        (
            "FROM golang:1.23 AS build\nWORKDIR /src\nCOPY . .\n"
            "RUN CGO_ENABLED=0 go build -o /usr/local/bin/shortlink .\n"
            "FROM scratch\n"
            "COPY --from=build /usr/local/bin/shortlink /usr/local/bin/shortlink\n"
            'CMD ["shortlink"]\n'
        ),
        frozenset(),
    ),
    "unnamed-stage-by-number": (
        COMPILER,
        (
            "FROM golang:1.23\nWORKDIR /src\nCOPY . .\n"
            "RUN CGO_ENABLED=0 go build -o /server .\n"
            "FROM scratch\nCOPY --from=0 /server /server\n"
            'ENTRYPOINT ["/server"]\n'
        ),
        frozenset(),
    ),
    "modules-in-a-stage-of-their-own": (
        COMPILER,
        (
            "FROM golang:1.23-alpine AS deps\nWORKDIR /src\n"
            "COPY go.mod ./\nRUN go mod download\n"
            "FROM deps AS build\nCOPY . .\n"
            "RUN CGO_ENABLED=0 go build -trimpath -ldflags=-s -o /out/shortlink .\n"
            "FROM scratch\nCOPY --from=build /out/shortlink /shortlink\n"
            "USER 65532:65532\n"
            'ENTRYPOINT ["/shortlink"]\n'
        ),
        frozenset(),
    ),
    "cross-compiled-for-the-target": (
        COMPILER,
        (
            "FROM --platform=$BUILDPLATFORM golang:1.23 AS build\n"
            "ARG TARGETOS TARGETARCH\nWORKDIR /src\nCOPY . .\n"
            "RUN CGO_ENABLED=0 GOOS=$TARGETOS GOARCH=$TARGETARCH "
            "go build -o /out/shortlink .\n"
            "FROM scratch\nCOPY --from=build /out/shortlink /shortlink\n"
            'ENTRYPOINT ["/shortlink"]\n'
        ),
        frozenset(),
    ),
    "alpine-final-stage": (
        COMPILER,
        (
            _BUILD + "FROM alpine:3.20\n"
            "COPY --from=build /out/shortlink /usr/local/bin/shortlink\n"
            'CMD ["shortlink"]\n'
        ),
        frozenset({"nothing-but-the-program"}),
    ),
    "named-volume": (
        MODULES,
        (
            "services:\n  web:\n    build: .\n"
            '    command: ["node", "--watch", "server.js"]\n'
            '    ports: ["3000:3000"]\n'
            "    volumes:\n      - .:/app\n      - node_modules:/app/node_modules\n"
            "volumes:\n  node_modules:\n"
        ),
        frozenset(),
    ),
    "long-form-mounts": (
        MODULES,
        (
            "services:\n  web:\n    build: .\n"
            '    command: ["node", "--watch", "server.js"]\n'
            '    ports: ["3000:3000"]\n'
            "    volumes:\n"
            "      - {type: bind, source: ., target: /app}\n"
            "      - {type: volume, target: /app/node_modules/}\n"
        ),
        frozenset(),
    ),
    # Phase 24. Each of these builds, starts and stores an upload on a real
    # daemon (tests/docker/test_unable_to_open_database_file.py), and the
    # first three are the ones a check for `chown` before `USER` would fail.
    "workdir-after-user": (
        NON_ROOT,
        (
            _SLIM + "WORKDIR /app\nCOPY . .\nRUN useradd --create-home app\n"
            "USER app\nWORKDIR /app/data\nWORKDIR /app\n" + _SERVE
        ),
        frozenset(),
    ),
    "user-before-workdir": (
        NON_ROOT,
        (
            _SLIM + "RUN useradd --create-home app\nUSER app\n"
            "WORKDIR /app\nCOPY . .\n" + _SERVE
        ),
        frozenset(),
    ),
    "copy-chown-into-a-new-directory": (
        NON_ROOT,
        (
            _SLIM + "RUN useradd --create-home app\n"
            "COPY --chown=app:app . /app/\nWORKDIR /app\nUSER app\n" + _SERVE
        ),
        frozenset(),
    ),
    "install-d-before-a-numeric-user": (
        NON_ROOT,
        (
            _SLIM + "WORKDIR /app\nCOPY . .\n"
            "RUN useradd --uid 10001 --create-home app "
            "&& install -d -o app -g app /app/data\nUSER 10001\n" + _SERVE
        ),
        frozenset(),
    ),
    "an-arbitrary-uid-through-group-0": (
        NON_ROOT,
        (
            _SLIM + "WORKDIR /app\nCOPY . .\n"
            "RUN mkdir -p /app/data && chgrp 0 /app/data "
            "&& chmod g+rwx /app/data\nUSER 4242\n" + _SERVE
        ),
        frozenset(),
    ),
    "chown-the-whole-app": (
        NON_ROOT,
        (
            _SLIM + "WORKDIR /app\nCOPY . .\n"
            "RUN useradd -m app && chown -R app:app /app\nUSER app\n" + _SERVE
        ),
        frozenset(),
    ),
    "a-group-the-user-is-in": (
        NON_ROOT,
        (
            _SLIM + "RUN useradd -N app\nWORKDIR /app\n"
            "RUN chgrp users /app && chmod 775 /app\nCOPY . .\nUSER app\n" + _SERVE
        ),
        frozenset(),
    ),
    "adduser-system-and-a-volume": (
        NON_ROOT,
        (
            _SLIM + "RUN adduser --system --group --no-create-home app\n"
            "WORKDIR /app\nCOPY . .\n"
            "RUN mkdir data && chown app: data\nVOLUME /app/data\n"
            "USER app:app\n" + _SERVE
        ),
        frozenset(),
    ),
    "user-from-a-build-argument": (
        NON_ROOT,
        (
            _SLIM + "ARG UID=10001\n"
            "RUN useradd --uid ${UID} app && mkdir -p /app/data "
            "&& chown ${UID}:${UID} /app/data\n"
            "WORKDIR /app\nCOPY . .\nUSER ${UID}\n" + _SERVE
        ),
        frozenset(),
    ),
    "trailing-slashes-and-a-mode": (
        MODULES,
        (
            "services:\n  web:\n    build: .\n"
            '    command: ["node", "--watch", "server.js"]\n'
            '    ports: ["3000:3000"]\n'
            "    volumes:\n      - ./:/app/:cached\n      - /app/node_modules/\n"
        ),
        frozenset(),
    ),
}


def grade_answer(slug: str, source: str) -> Verdict:
    directory = DOCKER / slug
    spec = load_exercise(directory).spec
    assert isinstance(spec, ContainerSpec)
    query = ParsedBuildQuery(
        context=context_files(directory / spec.context),
        editable=spec.stub,
        source=source,
    )
    return grade_query(spec, query)


@pytest.mark.parametrize("name", sorted(ANSWERS))
def test_a_right_answer_fails_nothing_it_should_not(name: str) -> None:
    slug, source, allowed = ANSWERS[name]
    verdict = grade_answer(slug, source)
    failed = {report.check_id for report in verdict.reports if not report.passed}
    assert failed == allowed, [
        (report.check_id, report.actual)
        for report in verdict.reports
        if not report.passed
    ]
    assert all(
        report.severity is Severity.ADVISORY
        for report in verdict.reports
        if report.check_id in allowed
    )


def test_an_undeclared_named_volume_is_refused_as_compose_refuses_it() -> None:
    """Not a counter-example: compose will not start it, so it does not parse.

    The obvious way to write the named-volume fix forgets the top-level block.
    Measured: `docker compose up` refuses the file with *refers to undefined
    volume*, and the grader says the same thing in its parse check rather
    than passing a stack that never starts.
    """
    source = ANSWERS["named-volume"][1].replace("volumes:\n  node_modules:\n", "")
    verdict = grade_answer(MODULES, source)
    [parsed] = [r for r in verdict.reports if r.check_id == DEFINITION_CHECK_ID]
    assert not parsed.passed
    assert parsed.actual is not None
    assert "refers to undefined volume node_modules" in parsed.actual
