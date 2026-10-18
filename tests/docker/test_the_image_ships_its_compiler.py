"""`the-image-ships-its-compiler`: the ticket, its counter-examples, its right answers.

Sizes are read the way the ticket reads them, from `docker images`, because
that is the number a solver will compare. `docker image inspect`'s `.Size`
answers a different question under the containerd image store (325 MB for
the stub, the compressed content), and a test that used it would be true and
would not be about the ticket.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

from tests.content.test_container_answers import ANSWERS, COMPILER
from tests.docker.conftest import (
    LABEL,
    BuildFailedError,
    build,
    docker,
    exercise,
    host_get,
    run,
)
from tests.docker.test_dockerfile_diagnoses import _layers_holding

if TYPE_CHECKING:
    from pathlib import Path

EXERCISE = exercise(COMPILER)

_UNITS = {"kB": 1e-3, "MB": 1.0, "GB": 1e3}


def megabytes(tag: str) -> float:
    """The SIZE column of `docker images`, in megabytes."""
    text = docker("images", "--format", "{{.Size}}", tag).strip()
    for unit, scale in _UNITS.items():
        if text.endswith(unit):
            return float(text[: -len(unit)]) * scale
    raise AssertionError(f"unexpected size {text!r}")


def built(tmp_path: Path, answer: str) -> str:
    tag, _ = build(EXERCISE.workspace(tmp_path, answer))
    return tag


def serves(tag: str) -> bool:
    container = run(tag, port=8080)
    return host_get(container.host_port(8080), path="/healthz") == "200"


def started_with(tag: str) -> str:
    """What `docker run` says when the container cannot start, or its logs."""
    return docker("run", "--rm", "--label", LABEL, tag, check=False)


# --- the ticket --------------------------------------------------------------


def test_the_stub_ships_the_toolchain_and_the_source(tmp_path: Path) -> None:
    tag = built(tmp_path, "Dockerfile")
    assert megabytes(tag) > 1300
    run_in = ("run", "--rm", "--label", LABEL, tag)
    assert docker(*run_in, "go", "version").startswith("go version go1.23")
    assert "main.go" in docker(*run_in, "ls", "/src").split()
    assert serves(tag)


def test_the_reference_is_small_holds_no_source_and_serves(tmp_path: Path) -> None:
    tag = built(tmp_path, "solution.Dockerfile")
    assert megabytes(tag) < 20
    assert _layers_holding(tag, tmp_path, "main.go") == []
    assert serves(tag)


# --- the counter-examples ----------------------------------------------------


def test_deleting_the_toolchain_saves_only_the_build_cache(tmp_path: Path) -> None:
    tag = built(tmp_path, "delete-the-toolchain.Dockerfile")
    assert 1200 < megabytes(tag) < 1300
    # Not `== [...]`: the golang base ships two hundred files called main.go
    # of its own, under /usr/share/doc and the Go source tree.
    assert "src/main.go" in _layers_holding(tag, tmp_path, "main.go")
    assert serves(tag)


def test_scratch_with_nothing_to_run_does_not_start(tmp_path: Path) -> None:
    tag = built(tmp_path, "nothing-to-run.Dockerfile")
    assert "no command specified" in started_with(tag)


def test_the_shell_form_on_scratch_has_no_shell(tmp_path: Path) -> None:
    tag = built(tmp_path, "shell-form-on-scratch.Dockerfile")
    said = started_with(tag)
    assert 'exec: "/bin/sh": stat /bin/sh: no such file or directory' in said


def test_copying_the_build_directory_ships_the_source(tmp_path: Path) -> None:
    tag = built(tmp_path, "copy-the-build-directory.Dockerfile")
    assert _layers_holding(tag, tmp_path, "main.go") == ["app/main.go"]
    assert serves(tag)


def test_a_binary_from_the_host_does_not_build_from_source(tmp_path: Path) -> None:
    with pytest.raises(BuildFailedError, match='"/shortlink": not found'):
        built(tmp_path, "binary-from-the-host.Dockerfile")


def test_without_cgo_disabled_the_binary_cannot_run_on_scratch(
    tmp_path: Path,
) -> None:
    """The notes' claim about `CGO_ENABLED=0`, which the grader cannot see."""
    workspace = EXERCISE.workspace(tmp_path, "solution.Dockerfile")
    dockerfile = workspace / "Dockerfile"
    dockerfile.write_text(
        dockerfile.read_text(encoding="utf-8").replace("CGO_ENABLED=0 ", ""),
        encoding="utf-8",
        newline="\n",
    )
    tag, _ = build(workspace)
    container = run(tag, port=8080)
    time.sleep(2)
    assert "exec /shortlink: no such file or directory" in container.logs()


# --- the answers the prompt does not rule out --------------------------------


@pytest.mark.parametrize(
    "name", sorted(name for name, (slug, _, _) in ANSWERS.items() if slug == COMPILER)
)
def test_every_accepted_answer_is_small_and_serves(tmp_path: Path, name: str) -> None:
    workspace = EXERCISE.workspace(tmp_path, "solution.Dockerfile")
    (workspace / "Dockerfile").write_text(
        ANSWERS[name][1], encoding="utf-8", newline="\n"
    )
    tag, _ = build(workspace)
    assert megabytes(tag) < 40
    assert _layers_holding(tag, tmp_path, "main.go") == []
    assert serves(tag)
