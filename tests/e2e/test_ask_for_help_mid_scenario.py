"""Asking for help four times across one attempt. The Phase 18 exit criterion.

Every adapter is the real one -- the shipped library, a real fixture, real
`git`, a real SQLite file -- and the test client stands in for the browser, as
in the Phase 8 journey beside this. `tests/web/test_tutor.py` covers the
endpoint against fakes and `tests/content/test_tutor_context.py` covers the
boundary for every exercise; what neither can show is the thing the feature is
*for*: **that the bundle is the attempt as it stands at the moment it is asked
for**, read back from the repository and the database rather than from anything
a request was holding.

**One test, and the answer typed in it is the wrong one on purpose.** The
flagship scenario's tempting mistake is `git reset --hard HEAD~1`, which leaves
a tidy local history and strands the published commit on `origin/main`. That is
the moment somebody asks a tutor what just happened, and it is the state a
bundle built only from what is reachable from HEAD would describe as fine. So
the second bundle is where this test earns its place: the stranded commit has
to be in it.
"""

from __future__ import annotations

import html
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient

from practice.composition import build_services
from practice.config import content_root
from practice.interface.web import create_app

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

REVERT = "git/revert-a-pushed-commit"

ORIGIN = "http://127.0.0.1"
BROWSER = {"origin": ORIGIN, "sec-fetch-site": "same-origin"}

#: The fixture's third commit: the one that broke the build and was pushed.
BAD_COMMIT = "Rename parse_line to parse"

#: The mistake as the attempt's log holds it. Quoted, because `CommandRun`
#: rebuilds the line from argv with `shlex.join` and `~` is a character a shell
#: would expand -- the same normalised form the console transcript shows, so the
#: bundle and the page beside it name the command identically.
RESET = "git reset --hard 'HEAD~1'"

#: The exercise's first hint and its last. The last one is the answer.
FIRST_HINT = "What does the build expect to find?"
LAST_HINT = "no force needed"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """The real object graph over disposable storage, against the real library."""
    services = build_services(
        content=content_root(),
        workspaces=tmp_path / "ws",
        database=tmp_path / "practice.db",
    )
    with TestClient(create_app(services), base_url=ORIGIN, headers=BROWSER) as client:
        yield client


def ask(client: TestClient, attempt_id: str) -> str:
    """The bundle as the textarea would hold it."""
    response = client.post(f"/api/attempt/{attempt_id}/context")
    assert response.status_code == 200
    assert 'id="tutor-text"' in response.text
    return html.unescape(response.text)


def test_each_bundle_is_the_attempt_at_the_moment_it_was_asked_for(
    client: TestClient,
) -> None:
    started = client.post(
        "/attempt", data={"exercise_id": REVERT}, follow_redirects=False
    )
    assert started.status_code == 303
    attempt_id = started.headers["location"].removeprefix("/attempt/")
    command_url = f"/api/attempt/{attempt_id}/command"

    # 1. Before anything is typed: the task, and the repository the fixture left,
    #    with the bad commit published. Nothing of the answer.
    fresh = ask(client, attempt_id)
    assert "## What I have done so far\n\nNothing yet." in fresh
    assert f"(HEAD, main, origin/main) {BAD_COMMIT}" in fresh
    assert "- Hints: 0 revealed, 4 not yet revealed" in fresh
    assert FIRST_HINT not in fresh
    assert LAST_HINT not in fresh
    assert "## The verdict" not in fresh

    # 2. The tempting mistake. `main` now looks clean, and the commit a teammate
    #    already has is reachable only from `origin/main` -- which the bundle
    #    still shows, because it reads every ref and not just HEAD.
    reset = client.post(command_url, data={"line": "git reset --hard HEAD~1"})
    assert 'class="entry ok"' in reset.text

    stranded = ask(client, attempt_id)
    assert f"**1.** Ran `{RESET}` (exit 0)" in stranded
    assert f"(origin/main) {BAD_COMMIT}" in stranded
    assert "(HEAD, main) " in stranded
    assert "- Commands: 1 run, 24 left." in stranded

    # 3. A hint, revealed in the workbench. It is in the next bundle, in its
    #    place in the sequence, and the hint that names the answer is not.
    client.post(f"/api/attempt/{attempt_id}/hint")

    hinted = ask(client, attempt_id)
    assert "**2.** Revealed hint 1:" in hinted
    assert FIRST_HINT in hinted
    assert LAST_HINT not in hinted

    # 4. Submitted as it stands, which fails -- and leaves the attempt open
    #    (ADR 0029). The bundle now carries the failure as the solver saw it,
    #    and still withholds the author's notes, because nothing is over yet.
    graded = client.post(f"/api/attempt/{attempt_id}/submit-scenario")
    assert '<p class="outcome fail">' in graded.text
    assert "The attempt is still open" in graded.text

    retrying = ask(client, attempt_id)
    assert "- Attempt: active, practice mode" in retrying
    assert "- Submissions: 1 failed so far" in retrying
    assert "**3.** Submitted, and it did not pass." in retrying
    assert "- Failed: " in retrying
    assert "## The author's notes" not in retrying

    # 5. Conceded. The same request is now a post-mortem: the verdict with its
    #    explanations, and the author's notes.
    client.post(f"/api/attempt/{attempt_id}/concede")

    post_mortem = ask(client, attempt_id)
    assert "- Attempt: completed, practice mode" in post_mortem
    assert "## The verdict\n\nOutcome: fail" in post_mortem
    assert "- Failed: " in post_mortem
    assert "## The author's notes" in post_mortem
    assert "no longer on disk" in post_mortem
    # The history is the database's, so it outlives the workspace it describes.
    assert f"**1.** Ran `{RESET}` (exit 0)" in post_mortem
