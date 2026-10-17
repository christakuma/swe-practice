"""`dockerize-a-python-web-service`: each requirement in the prompt, observed."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from tests.docker.conftest import build, exercise, host_get, run

if TYPE_CHECKING:
    from pathlib import Path

EXERCISE = exercise("dockerize-a-python-web-service")


def test_the_reference_answers_from_the_host_and_stops_at_once(tmp_path: Path) -> None:
    tag, _ = build(EXERCISE.workspace(tmp_path, "solution.Dockerfile"))
    container = run(tag)
    assert host_get(container.host_port()) == "200"
    assert container.timed_stop() < 3
    assert container.exit_code() == 0


def test_the_default_bind_answers_inside_but_not_from_the_host(tmp_path: Path) -> None:
    tag, _ = build(EXERCISE.workspace(tmp_path, "default-bind.Dockerfile"))
    container = run(tag)
    assert container.exec_get() == "200"
    assert host_get(container.host_port(), attempts=6) != "200"
    assert "Listening at: http://127.0.0.1:8000" in container.logs()


def test_a_bare_port_bind_is_every_interface(tmp_path: Path) -> None:
    """`--bind :8000` passes `serves-every-interface`; this is why that is right."""
    workspace = EXERCISE.workspace(tmp_path, "solution.Dockerfile")
    dockerfile = workspace / "Dockerfile"
    dockerfile.write_text(
        dockerfile.read_text(encoding="utf-8").replace("0.0.0.0:8000", ":8000"),
        encoding="utf-8",
        newline="\n",
    )
    tag, _ = build(workspace)
    assert host_get(run(tag).host_port()) == "200"


def test_the_shell_form_waits_out_docker_stop(tmp_path: Path) -> None:
    tag, _ = build(EXERCISE.workspace(tmp_path, "shell-form-cmd.Dockerfile"))
    container = run(tag)
    assert host_get(container.host_port()) == "200"
    assert container.timed_stop() >= 9
    assert container.exit_code() == 137


def test_copying_everything_first_reinstalls_on_a_code_change(tmp_path: Path) -> None:
    for answer, reused in (
        ("solution.Dockerfile", True),
        ("copy-everything-first.Dockerfile", False),
    ):
        workspace = EXERCISE.workspace(tmp_path, answer)
        build(workspace)
        app = workspace / "app.py"
        # Unique per run: BuildKit keys its cache on content, so the same edit
        # made by an earlier run would be a cache hit for the wrong reason.
        edit = f"\n# edited {uuid.uuid4().hex}\n"
        app.write_text(app.read_text(encoding="utf-8") + edit, "utf-8")
        _, output = build(workspace, progress=True)
        # BuildKit numbers each step (`#8 [4/6] RUN pip install ...`) and reports
        # a cache hit as a separate `#8 CACHED` line.
        lines = output.splitlines()
        [step] = {line.split()[0] for line in lines if "RUN pip install" in line}
        cached = f"{step} CACHED" in lines
        assert cached is reused, f"{answer}:\n{output}"
