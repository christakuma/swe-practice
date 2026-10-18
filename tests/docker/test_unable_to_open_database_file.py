"""`unable-to-open-database-file`: the ticket, its counter-examples, its right answers.

The grader reads ownership off the definition (`adapters/container/
filesystem.py`); this file is where each rule it follows is shown to be what
BuildKit does. A right answer here is one that **starts and stores an
upload**, not one whose directory looks right: `POST` writes a row through
SQLite into `/app/data`, so a service that answers it has written its data.
"""

from __future__ import annotations

import time
import urllib.request
from typing import TYPE_CHECKING

import pytest

from tests.content.test_container_answers import ANSWERS, NON_ROOT
from tests.docker.conftest import (
    LABEL,
    BuildFailedError,
    Container,
    build,
    docker,
    exercise,
    run,
)

if TYPE_CHECKING:
    from pathlib import Path

EXERCISE = exercise(NON_ROOT)


def built(tmp_path: Path, answer: str) -> str:
    tag, _ = build(EXERCISE.workspace(tmp_path, answer))
    return tag


def in_image(tag: str, *command: str, user: str | None = None) -> str:
    who = ("--user", user) if user is not None else ()
    return docker("run", "--rm", "--label", LABEL, *who, tag, *command).strip()


def stores_an_upload(container: Container) -> bool:
    """`POST` once and read the count back, retrying while the server starts."""
    port = container.host_port(8000)
    for _ in range(20):
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/report.pdf", data=b"hello", method="POST"
            )
            with urllib.request.urlopen(request, timeout=5) as response:  # noqa: S310
                return b'"bytes": 5' in response.read()
        except OSError:
            time.sleep(0.5)
    return False


def exits_with(tag: str) -> str:
    """The last line a container that stops at start-up printed."""
    container = run(tag)
    time.sleep(3)
    assert container.exit_code() == 1
    return container.logs().strip().splitlines()[-1]


# --- the ticket --------------------------------------------------------------


def test_the_stub_cannot_open_its_database(tmp_path: Path) -> None:
    tag = built(tmp_path, "Dockerfile")
    assert exits_with(tag) == "sqlite3.OperationalError: unable to open database file"
    assert in_image(tag, "id") == "uid=1000(app) gid=1000(app) groups=1000(app)"
    assert in_image(tag, "stat", "-c", "%U:%G %a", "/app", "/app/data") == (
        "root:root 755\nroot:root 755"
    )


def test_the_reference_starts_and_stores_an_upload(tmp_path: Path) -> None:
    tag = built(tmp_path, "solution.Dockerfile")
    assert in_image(tag, "stat", "-c", "%U:%G %a", "/app/data") == "app:app 755"
    assert stores_an_upload(run(tag))


# --- the counter-examples ----------------------------------------------------


def test_dropping_the_user_starts_as_root(tmp_path: Path) -> None:
    tag = built(tmp_path, "drop-the-user.Dockerfile")
    assert in_image(tag, "id", "-u") == "0"
    assert stores_an_upload(run(tag))


def test_copy_chown_leaves_the_directory_it_copies_into_to_root(
    tmp_path: Path,
) -> None:
    tag = built(tmp_path, "copy-with-chown.Dockerfile")
    assert in_image(tag, "stat", "-c", "%U:%G", "/app", "/app/app.py") == (
        "root:root\napp:app"
    )
    assert (
        exits_with(tag) == "PermissionError: [Errno 13] Permission denied: '/app/data'"
    )


def test_chown_after_user_stops_the_build(tmp_path: Path) -> None:
    with pytest.raises(BuildFailedError, match="Operation not permitted"):
        built(tmp_path, "chown-after-user.Dockerfile")


def test_chmod_777_lets_nobody_write_the_ledger(tmp_path: Path) -> None:
    tag = built(tmp_path, "world-writable.Dockerfile")
    assert stores_an_upload(run(tag))
    in_image(tag, "touch", "/app/data/planted", user="nobody")


def test_the_notes_volume_claim_a_named_volume_keeps_the_owner(
    tmp_path: Path,
) -> None:
    """The notes: a new named volume is filled from the image, owner and all."""
    tag = built(tmp_path, "solution.Dockerfile")
    volume = f"swe-practice-test-{tag.rsplit(':', 1)[1]}"
    try:
        mounted = docker(
            "run", "--rm", "--label", LABEL, "-v", f"{volume}:/app/data",
            tag, "stat", "-c", "%U:%G", "/app/data",
        )  # fmt: skip
        assert mounted.strip() == "app:app"
    finally:
        docker("volume", "rm", "-f", volume, check=False)


# --- the answers the prompt does not rule out --------------------------------


@pytest.mark.parametrize(
    "name", sorted(name for name, (slug, _, _) in ANSWERS.items() if slug == NON_ROOT)
)
def test_every_accepted_answer_stores_an_upload_as_non_root(
    tmp_path: Path, name: str
) -> None:
    workspace = EXERCISE.workspace(tmp_path, "solution.Dockerfile")
    (workspace / "Dockerfile").write_text(
        ANSWERS[name][1], encoding="utf-8", newline="\n"
    )
    tag, _ = build(workspace)
    assert in_image(tag, "id", "-u") != "0"
    assert stores_an_upload(run(tag))
