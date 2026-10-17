"""The two compose tickets, against a real Postgres.

Each case brings a stack up under its own project name and takes it down with
its volumes, so one case cannot hand a warm database to the next — which
would hide the startup race the second exercise is about.
"""

from __future__ import annotations

import json
import subprocess
import time
import uuid
from typing import TYPE_CHECKING

import pytest
import yaml

from tests.docker.conftest import exercise

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from tests.docker.conftest import Exercise

REACH = exercise("the-api-cannot-reach-the-database")
RACE = exercise("the-api-starts-before-the-database")


class Stack:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace
        self.project = f"swe-practice-test-{uuid.uuid4().hex[:8]}"

    def compose(
        self, *args: str, timeout: float = 300
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            ["docker", "compose", "-p", self.project, *args],  # noqa: S607
            cwd=self.workspace, capture_output=True, text=True,
            timeout=timeout, check=False,
        )  # fmt: skip

    def up(self) -> subprocess.CompletedProcess[str]:
        return self.compose("up", "-d", "--build", "--quiet-pull")

    def api_state(self) -> str:
        result = self.compose("ps", "-a", "--format", "json", "api")
        rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        return rows[0]["State"] if rows else "missing"

    def api_logs(self) -> str:
        return self.compose("logs", "--no-color", "api").stdout

    def health(self) -> dict[str, object] | None:
        script = (
            "import urllib.request, json;"
            "print(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"
            ".read().decode())"
        )
        result = self.compose("exec", "-T", "api", "python", "-c", script)
        if result.returncode != 0:
            return None
        return dict(json.loads(result.stdout))

    def down(self) -> None:
        self.compose("down", "-v", "--remove-orphans", timeout=120)


type MakeStack = Callable[[Exercise, str], Stack]


@pytest.fixture
def stack(tmp_path: Path) -> Iterator[MakeStack]:
    made: list[Stack] = []

    def make(ex: Exercise, answer: str) -> Stack:
        workspace = ex.workspace(tmp_path, answer)
        # The ticket publishes the API on host port 8000. The tests ask it from
        # inside instead, so drop that one; a db port a case publishes stays,
        # because publishing it is what `via-the-host` is about.
        compose = workspace / "compose.yaml"
        document = yaml.safe_load(compose.read_text(encoding="utf-8"))
        document["services"]["api"].pop("ports", None)
        compose.write_text(yaml.safe_dump(document), encoding="utf-8")
        created = Stack(workspace)
        made.append(created)
        return created

    yield make
    for created in made:
        created.down()


def _wait_healthy(stack: Stack, seconds: float = 40) -> dict[str, object] | None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        found = stack.health()
        if found is not None:
            return found
        time.sleep(1)
    return None


# --- the-api-cannot-reach-the-database ---------------------------------------


def test_localhost_is_the_apis_own_loopback(stack: MakeStack) -> None:
    running = stack(REACH, "compose.yaml")
    assert running.up().returncode == 0
    time.sleep(6)
    assert "database localhost:5432 refused the connection" in running.api_logs()
    assert running.api_state() == "running"


@pytest.mark.parametrize(
    ("answer", "works"),
    [
        ("solution.compose.yaml", True),
        ("loopback-by-number.compose.yaml", False),
        ("via-the-host.compose.yaml", True),
        ("host-networking.compose.yaml", False),
    ],
)
def test_which_answers_reach_the_database(
    stack: MakeStack, answer: str, works: bool
) -> None:
    """`via-the-host` works on Docker Desktop. It is wrong for another reason."""
    running = stack(REACH, answer)
    assert running.up().returncode == 0
    found = _wait_healthy(running, 40 if works else 8)
    assert (found is not None and found["reachable"] is True) is works, (
        running.api_logs()
    )


# --- the-api-starts-before-the-database --------------------------------------


def test_short_depends_on_loses_the_race(stack: MakeStack) -> None:
    running = stack(RACE, "compose.yaml")
    assert running.up().returncode == 0
    time.sleep(6)
    assert running.api_state() == "exited"
    assert "FATAL: could not connect to the database at db:5432" in running.api_logs()


def test_the_reference_waits_and_connects(stack: MakeStack) -> None:
    running = stack(RACE, "solution.compose.yaml")
    result = running.up()
    assert result.returncode == 0, result.stderr
    found = _wait_healthy(running)
    assert found is not None, running.api_logs()
    assert found["reachable"] is True


def test_a_condition_with_no_healthcheck_is_refused(stack: MakeStack) -> None:
    running = stack(RACE, "condition-without-a-healthcheck.compose.yaml")
    result = running.up()
    assert result.returncode != 0
    assert "healthcheck" in result.stderr


def test_a_healthcheck_nobody_waits_for_changes_nothing(stack: MakeStack) -> None:
    running = stack(RACE, "healthcheck-nobody-waits-for.compose.yaml")
    assert running.up().returncode == 0
    time.sleep(6)
    assert running.api_state() == "exited"


def test_restarting_until_it_works_does_eventually(stack: MakeStack) -> None:
    """Wrong for what it costs, not for failing: it crash-loops first."""
    running = stack(RACE, "restart-until-it-works.compose.yaml")
    assert running.up().returncode == 0
    found = _wait_healthy(running, 60)
    assert found is not None
    assert running.api_logs().count("FATAL") >= 1
