"""The honesty tier: every ticket's symptom, reproduced against a real daemon.

**Opt-in, and never part of the gate** (ADR 0030). `tests/content/` proves the
grader agrees with the author; it cannot prove the author is right about
Docker — that a shell-form `CMD` really waits out `docker stop`, or that a
gunicorn on `127.0.0.1` really resets a published port. Phase 17 found that a
claim nobody executed is a guess (ADR 0022), and a Docker exercise is nothing
*but* claims about a system the suite never runs.

So these tests build the stub, the reference and the counter-examples into real
images and watch them misbehave. They need a running daemon and pull base
images, which is why they are skipped unless `PRACTICE_DOCKER_TESTS=1`: CI on
Windows cannot run Linux containers, and the project stays offline everywhere
else. Run them after changing an exercise:

    PRACTICE_DOCKER_TESTS=1 uv run pytest -q --no-cov -n0 tests/docker
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from practice.adapters.content import load_exercise
from practice.config import content_root
from practice.domain.exercise import ContainerSpec

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

_ENABLED = os.environ.get("PRACTICE_DOCKER_TESTS") == "1"

#: Every image and container these tests create carries this label, so the
#: teardown removes exactly what the run made and nothing the user owns.
LABEL = "swe-practice.honesty-tier"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip this directory's tests, and only this directory's.

    **A collection hook in a conftest is not scoped to its directory**: pytest
    hands it every item in the session. The first version skipped all nine
    thousand tests in the suite whenever the variable was unset -- which is
    how CI runs -- and the gate failed only because coverage fell to 45%.
    """
    if _ENABLED:
        return
    skip = pytest.mark.skip(reason="set PRACTICE_DOCKER_TESTS=1 to run against Docker")
    here = Path(__file__).parent
    for item in items:
        if item.path.is_relative_to(here):
            item.add_marker(skip)


def docker(*args: str, timeout: float = 300, check: bool = True) -> str:
    """Run the docker CLI and hand back stdout, or raise with stderr in it."""
    result = subprocess.run(  # noqa: S603 - fixed program, test-authored arguments
        ["docker", *args],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode != 0:
        raise AssertionError(
            f"docker {' '.join(args)} exited {result.returncode}:\n{result.stderr}"
        )
    return result.stdout + result.stderr if not check else result.stdout


@dataclass(frozen=True, slots=True)
class Exercise:
    directory: Path
    spec: ContainerSpec

    def workspace(self, tmp_path: Path, answer: str) -> Path:
        """The context plus one answer file under the editable name, as provisioned."""
        target = tmp_path / f"ws-{uuid.uuid4().hex[:8]}"
        shutil.copytree(self.directory / self.spec.context, target)
        shutil.copyfile(self.directory / answer, target / self.spec.stub)
        return target


def exercise(slug: str) -> Exercise:
    directory = content_root() / "docker" / slug
    spec = load_exercise(directory).spec
    assert isinstance(spec, ContainerSpec)
    return Exercise(directory=directory, spec=spec)


def build(
    workspace: Path,
    *,
    progress: bool = False,
    build_args: Mapping[str, str] | None = None,
) -> tuple[str, str]:
    """`docker build` the workspace; the image tag and the build's own output."""
    tag = f"swe-practice-test:{uuid.uuid4().hex[:12]}"
    args = ["build", "--label", LABEL, "-t", tag]
    if progress:
        args += ["--progress=plain"]
    for name, value in (build_args or {}).items():
        args += ["--build-arg", f"{name}={value}"]
    result = subprocess.run(  # noqa: S603
        ["docker", *args, str(workspace)],  # noqa: S607
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if result.returncode != 0:
        raise BuildFailedError(result.stderr)
    return tag, result.stderr + result.stdout


class BuildFailedError(AssertionError):
    """`docker build` refused the file, with the builder's own message."""


@dataclass(frozen=True, slots=True)
class Container:
    id: str

    def host_port(self, port: int = 8000) -> int:
        mapping = docker("port", self.id, str(port)).strip().splitlines()[0]
        return int(mapping.rsplit(":", 1)[1])

    def logs(self) -> str:
        return docker("logs", self.id, check=False)

    def exit_code(self) -> int:
        state = json.loads(docker("inspect", "--format", "{{json .State}}", self.id))
        return int(state["ExitCode"])

    def timed_stop(self) -> float:
        started = time.monotonic()
        docker("stop", self.id, timeout=60)
        return time.monotonic() - started

    def exec_get(self, port: int = 8000) -> str:
        """Fetch `/` from *inside* the container, where loopback is the app's."""
        url = f"http://127.0.0.1:{port}/"
        script = f"import urllib.request; print(urllib.request.urlopen({url!r}).status)"
        return docker("exec", self.id, "python", "-c", script, check=False).strip()


def run(tag: str, *args: str) -> Container:
    """Start a container detached, publishing 8000 on a free loopback port."""
    container_id = docker(
        "run", "-d", "--label", LABEL, "-p", "127.0.0.1::8000", *args, tag
    ).strip()
    return Container(id=container_id)


def host_get(port: int, *, attempts: int = 20) -> str:
    """`GET /` from the host, as the ticket's `curl` did: a status, or the error."""
    last = ""
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/", timeout=5
            ) as response:
                return str(response.status)
        except (urllib.error.URLError, ConnectionError, OSError) as exc:
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(0.5)
    return last


@pytest.fixture(scope="session", autouse=True)
def _clean_up() -> Iterator[None]:
    yield
    if not _ENABLED:
        return
    containers = docker("ps", "-aq", "--filter", f"label={LABEL}").split()
    if containers:
        docker("rm", "-f", *containers, check=False)
    images = docker("images", "-q", "--filter", f"label={LABEL}").split()
    if images:
        docker("rmi", "-f", *set(images), check=False)
