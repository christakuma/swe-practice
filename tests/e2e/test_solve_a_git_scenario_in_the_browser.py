"""One git scenario, driven start to finish over HTTP. The Phase 8 exit criterion.

*"A git scenario driven start to finish in the browser, with the graph visibly
changing after each command."* Every adapter here is the real one — the filesystem
content library, the subprocess provisioner running a real fixture, real `git`, a
real SQLite file — and the only thing standing in for a browser is the test client,
which speaks the request a browser sends because `SameOriginMiddleware` refuses
anything that does not.

**One test, deliberately**, like its Phase 7 sibling. It provisions a repository and
starts a dozen `git` processes, and §9's rule is that anything assertable one layer
down belongs one layer down: the route, the fragments and the refusals are covered
in `tests/web/` against fakes in milliseconds. What only this layer can show is that
the pieces compose — browse, start, look around, reveal a hint, revert, push, submit
— and that the repository the panel drew is the repository the grader graded.

**The answer typed here is not the exercise's own `solution.cmds`.** The point of
grading the end state is that the tool never punishes a correct answer it did not
anticipate, and a journey test that replayed the answer key would be the one place
that assumption went untested. The CLI journey test makes the same choice for the
same reason.
"""

from __future__ import annotations

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


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """The real object graph over disposable storage, against the real library.

    The *real* content root: this is the test that should break if the shipped git
    scenario stops being solvable through the web app, which is the question
    `tests/web/` deliberately does not ask.
    """
    services = build_services(
        content=content_root(),
        workspaces=tmp_path / "ws",
        database=tmp_path / "practice.db",
    )
    with TestClient(create_app(services), base_url=ORIGIN, headers=BROWSER) as client:
        yield client


def test_a_scenario_is_browsed_started_driven_and_graded(
    client: TestClient, tmp_path: Path
) -> None:
    """Look around, reveal a hint, revert, push, submit. All over HTTP."""
    listing = client.get("/browse", params={"kind": "git_scenario"})
    assert listing.status_code == 200
    assert "Undo a commit that is already on origin" in listing.text

    started = client.post(
        "/attempt", data={"exercise_id": REVERT}, follow_redirects=False
    )
    assert started.status_code == 303
    workbench_url = started.headers["location"]
    attempt_id = workbench_url.removeprefix("/attempt/")

    # The page the fixture leaves behind: a console with nothing in it, and a repo
    # panel drawn from a repository that already has a problem in it.
    workbench = client.get(workbench_url)
    assert workbench.status_code == 200
    assert 'id="console-log"' in workbench.text
    assert 'id="repo-state"' in workbench.text
    assert 'class="commit-graph"' in workbench.text
    # The bad commit, on `main` and on `origin/main`: the published state.
    assert "Rename parse_line to parse" in workbench.text
    assert "origin/main" in workbench.text

    command_url = f"/api/attempt/{attempt_id}/command"

    # Look before leaping, which is one of the exercise's own advisory checks.
    looked = client.post(command_url, data={"line": "git log --oneline --decorate"})
    assert looked.status_code == 200
    assert 'class="entry ok"' in looked.text
    # One response, the appended output *and* the re-rendered panel: PLAN.md §8.4.
    assert 'id="repo-state"' in looked.text
    assert 'hx-swap-oob="true"' in looked.text
    assert "1 of 25 commands used" in looked.text

    # The policy is the exercise's, applied to what a solver actually typed: no
    # shell, so a redirect is refused with a pointer to the virtual `write`.
    refused = client.post(command_url, data={"line": "git log > out.txt"})
    assert 'class="entry refused"' in refused.text
    assert "write" in refused.text
    # And it did not run, so it did not spend anything.
    assert "hx-swap-oob" not in refused.text

    # A hint, recorded on the attempt because it is something the solver did.
    hint = client.post(f"/api/attempt/{attempt_id}/hint")
    assert hint.status_code == 200
    assert "1 of 4" in hint.text

    # The fix: a new commit that undoes the bad one, leaving it reachable.
    reverted = client.post(command_url, data={"line": "git revert --no-edit HEAD"})
    assert 'class="entry ok"' in reverted.text
    # The graph has grown a commit, and the panel came back with it.
    assert reverted.text.count('class="node commit"') >= 4

    # Not published yet: `origin/main` is still behind, and the panel says so by
    # drawing it on a different commit from the one HEAD is on.
    before_push = client.get(workbench_url)
    assert "Revert" in before_push.text

    pushed = client.post(command_url, data={"line": "git push origin main"})
    assert 'class="entry ok"' in pushed.text

    graded = client.post(f"/api/attempt/{attempt_id}/submit-scenario")
    assert graded.status_code == 200
    # Required checks all green; `looked-before-leaping` satisfied by the `git log`
    # above, so this is a clean pass rather than a pass with advisories.
    assert '<p class="outcome pass">' in graded.text
    assert 'class="check failed"' not in graded.text

    # The page a reload gives is the verdict the submission gave, because both
    # render `partials/verdict.html` over the same stored attempt.
    reloaded = client.get(workbench_url)
    assert reloaded.status_code == 200
    assert graded.text.strip() in reloaded.text
    # The console is gone with the workspace it drove, and the panel says why
    # rather than refusing to render.
    assert 'id="console-log"' not in reloaded.text
    assert "disposed of" in reloaded.text
    # The hint is still on the record, which is the number Phase 9 reads.
    assert "1 of 4 hints were" in reloaded.text

    # Nothing left behind: submission disposed of the workspace, and the attempt
    # row survives in a database that outlives the request.
    assert list((tmp_path / "ws").iterdir()) == []
    assert (tmp_path / "practice.db").is_file()
    assert "Nothing open" in client.get("/").text
