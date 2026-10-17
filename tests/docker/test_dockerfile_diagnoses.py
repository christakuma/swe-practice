"""The three Dockerfile tickets, and every claim their counter-examples make."""

from __future__ import annotations

import io
import json
import tarfile
import time
from typing import TYPE_CHECKING

import pytest

from tests.docker.conftest import LABEL, build, docker, exercise, host_get, run

if TYPE_CHECKING:
    from pathlib import Path

RESET = exercise("connection-reset-from-the-host")
STOP = exercise("docker-stop-takes-ten-seconds")
SECRET = exercise("the-secret-still-in-the-image")

KEY = "pk_fake_8c1f0e7a_not_a_real_key"


# --- connection-reset-from-the-host ------------------------------------------


def test_the_stub_resets_from_the_host_and_answers_inside(tmp_path: Path) -> None:
    tag, _ = build(RESET.workspace(tmp_path, "Dockerfile"))
    container = run(tag)
    assert container.exec_get() == "200"
    assert host_get(container.host_port(), attempts=6) != "200"


@pytest.mark.parametrize(
    ("answer", "reachable"),
    [
        ("solution.Dockerfile", True),
        ("wrong-port.Dockerfile", False),
        ("loopback-spelled-out.Dockerfile", False),
        ("shell-form-fix.Dockerfile", True),
    ],
)
def test_which_answers_reach_the_host(
    tmp_path: Path, answer: str, reachable: bool
) -> None:
    """`shell-form-fix` does reach it: what it fails is `docker stop`, below."""
    tag, _ = build(RESET.workspace(tmp_path, answer))
    status = host_get(run(tag).host_port(), attempts=8 if reachable else 6)
    assert (status == "200") is reachable, status


def test_the_shell_form_fix_waits_out_docker_stop(tmp_path: Path) -> None:
    tag, _ = build(RESET.workspace(tmp_path, "shell-form-fix.Dockerfile"))
    container = run(tag)
    assert host_get(container.host_port()) == "200"
    assert container.timed_stop() >= 9


# --- docker-stop-takes-ten-seconds -------------------------------------------


@pytest.mark.parametrize(
    ("answer", "slow", "code", "clean"),
    [
        ("Dockerfile", True, 137, False),
        ("solution.Dockerfile", False, 0, True),
        ("sh-dash-c.Dockerfile", True, 137, False),
        ("stopsignal-sigkill.Dockerfile", False, 137, False),
    ],
)
def test_how_each_answer_stops(
    tmp_path: Path, answer: str, slow: bool, code: int, clean: bool
) -> None:
    """The ticket and both counter-examples. SIGKILL is fast and still not clean."""
    tag, _ = build(STOP.workspace(tmp_path, answer))
    container = run(tag)
    time.sleep(3)
    took = container.timed_stop()
    assert (took >= 9) is slow, f"{answer} took {took:.1f}s"
    assert container.exit_code() == code
    assert ("worker stopped cleanly" in container.logs()) is clean


# --- the-secret-still-in-the-image -------------------------------------------


def _layers_holding(tag: str, tmp_path: Path, name: str) -> list[str]:
    """Every regular file called `name` in any layer of the saved image."""
    archive = tmp_path / "image.tar"
    docker("save", tag, "-o", str(archive))
    found = []
    with tarfile.open(archive) as outer:
        for member in outer.getmembers():
            handle = outer.extractfile(member) if member.isfile() else None
            if handle is None:
                continue
            try:
                with tarfile.open(fileobj=io.BytesIO(handle.read())) as layer:
                    found += [
                        inner.name
                        for inner in layer.getmembers()
                        if inner.isfile() and inner.name.rsplit("/", 1)[-1] == name
                    ]
            except tarfile.TarError:
                continue
    return found


def _config_env(tag: str) -> list[str]:
    return list(json.loads(docker("inspect", "--format", "{{json .Config.Env}}", tag)))


def _built(tmp_path: Path, answer: str) -> str:
    """Build as a careless CI job would: with the key passed as a build argument."""
    tag, _ = build(
        SECRET.workspace(tmp_path, answer), build_args={"PAYMENTS_API_KEY": KEY}
    )
    return tag


def test_the_stub_deletes_the_file_and_ships_it(tmp_path: Path) -> None:
    tag = _built(tmp_path, "Dockerfile")
    listing = docker("run", "--rm", "--label", LABEL, tag, "ls", "-a", "/app")
    assert ".env" not in listing.split()
    assert _layers_holding(tag, tmp_path, ".env") == ["app/.env"]


def test_the_reference_ships_no_key_anywhere(tmp_path: Path) -> None:
    tag = _built(tmp_path, "solution.Dockerfile")
    assert _layers_holding(tag, tmp_path, ".env") == []
    assert not any(KEY in entry for entry in _config_env(tag))
    assert host_get(run(tag).host_port()) == "200"


def test_a_build_argument_puts_the_key_in_the_config(tmp_path: Path) -> None:
    tag = _built(tmp_path, "key-as-a-build-argument.Dockerfile")
    assert _layers_holding(tag, tmp_path, ".env") == []
    assert f"PAYMENTS_API_KEY={KEY}" in _config_env(tag)


def test_copying_only_the_entrypoint_does_not_start(tmp_path: Path) -> None:
    tag = _built(tmp_path, "copy-only-the-entrypoint.Dockerfile")
    container = run(tag)
    time.sleep(3)
    assert "ModuleNotFoundError: No module named 'pricing'" in container.logs()


def test_a_builder_stage_that_deletes_hands_on_nothing(tmp_path: Path) -> None:
    """The case `_Held.visible` exists for: a correct answer the model must pass."""
    workspace = SECRET.workspace(tmp_path, "solution.Dockerfile")
    (workspace / "Dockerfile").write_text(
        "FROM python:3.12-slim AS build\nWORKDIR /app\nCOPY . .\nRUN rm -f .env\n"
        "FROM python:3.12-slim\nWORKDIR /app\nCOPY --from=build /app /app\n"
        'CMD ["python", "app.py"]\n',
        encoding="utf-8",
        newline="\n",
    )
    tag, _ = build(workspace, build_args={"PAYMENTS_API_KEY": KEY})
    assert _layers_holding(tag, tmp_path, ".env") == []
