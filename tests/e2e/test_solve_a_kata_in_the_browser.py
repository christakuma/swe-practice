"""One kata, solved entirely through HTTP. The Phase 7 exit criterion.

*"A kata solved entirely in the browser with the network disconnected."* Every
adapter here is the real one — the filesystem content library, the subprocess
provisioner, a real pytest run, a real SQLite file — and the only thing standing
in for a browser is the test client, which speaks the same request the browser
sends because `SameOriginMiddleware` refuses anything that does not.

**One test, deliberately.** It costs two pytest subprocesses and a provisioned
workspace, and §9's rule is that anything assertable one layer down belongs one
layer down: the route, the form parsing and the fragment are covered in
`tests/web/test_submit.py` against a fake grader in milliseconds. What only this
layer can show is that the pieces compose — browse, start, submit, grade, and a
workspace that cleans itself up.

**The network claim is structural, not asserted here.** Nothing to disconnect:
`tests/web/test_offline.py` proves no page or asset of ours names a remote host,
`test_vendored_assets.py` pins the four files that are not ours, and the build
excludes the one module that can open a socket. A test that pulled the interface
down would prove less than those three and take longer.
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

TWO_SUM = "katas/two-sum"

#: Where the test client claims to be. A loopback origin, because the `Host`
#: check refuses anything else -- a browser would be pointed here too.
ORIGIN = "http://127.0.0.1"

BROWSER = {"origin": ORIGIN, "sec-fetch-site": "same-origin"}

#: What a solver arrives at: the one-pass dict, written out longhand.
SOLVED = """\
def two_sum(numbers, target):
    seen = {}
    for index, value in enumerate(numbers):
        complement = target - value
        if complement in seen:
            return (seen[complement], index)
        seen[value] = index
    raise ValueError("no pair of values adds up to the target")
"""

#: Correct on the first example and nothing else, so the verdict has something to
#: say. A stub would fail every check at once, which proves the suite ran and not
#: that the page can report a *mixture*.
WRONG = """\
def two_sum(numbers, target):
    return (0, 1)
"""


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """The real object graph, over disposable storage.

    The *real* content root: this is the one test that should break if the
    shipped library stops being solvable through the web app, which is the
    question `tests/web/` deliberately does not ask.
    """
    services = build_services(
        content=content_root(),
        workspaces=tmp_path / "ws",
        database=tmp_path / "practice.db",
    )
    with TestClient(create_app(services), base_url=ORIGIN, headers=BROWSER) as client:
        yield client


def test_a_kata_is_browsed_started_submitted_and_graded(
    client: TestClient, tmp_path: Path
) -> None:
    """Browse, start, submit a wrong answer, fix it, pass. All over HTTP.

    The wrong answer first because that is the loop the product is: a verdict
    that reported nothing useful about a near-miss would make the second half
    pointless. `(0, 1)` is right for the first example and wrong for the rest, so
    the hidden suite has to disagree with itself across checks -- which is the
    thing one check per test buys.
    """
    listing = client.get("/browse", params={"kind": "kata"})
    assert listing.status_code == 200
    assert "Two Sum" in listing.text

    started = client.post(
        "/attempt", data={"exercise_id": TWO_SUM}, follow_redirects=False
    )
    assert started.status_code == 303
    workbench_url = started.headers["location"]

    # The editor opens on the exercise's own stub, read out of the workspace the
    # provisioner just built -- so what is on screen is what this attempt starts
    # from, not what the library currently says.
    workbench = client.get(workbench_url)
    assert workbench.status_code == 200
    assert "def two_sum" in workbench.text
    assert "NotImplementedError" in workbench.text

    attempt_id = workbench_url.removeprefix("/attempt/")
    submit_url = f"/api/attempt/{attempt_id}/submit"
    assert submit_url in workbench.text

    near_miss = client.post(
        submit_url, data={"source": WRONG, "time": "O(n)", "space": "O(1)"}
    )
    assert near_miss.status_code == 200
    # The outcome element, not the substring "fail": `class="check failed"` would
    # match that, and an assertion a stylesheet can satisfy is not an assertion.
    assert '<p class="outcome fail">' in near_miss.text
    # A mixture, which is what one check per test buys and what a single
    # pass/fail could not show: `(0, 1)` is right for the first example.
    assert 'class="check passed"' in near_miss.text
    assert 'class="check failed"' in near_miss.text

    # A second attempt, because the first is finished: submission completes it
    # and disposes of its workspace, which is §8.1's lifecycle and not something
    # the web app gets to opt out of.
    again = client.post(
        "/attempt", data={"exercise_id": TWO_SUM}, follow_redirects=False
    )
    second_url = again.headers["location"]
    second_id = second_url.removeprefix("/attempt/")

    passed = client.post(
        f"/api/attempt/{second_id}/submit",
        data={"source": SOLVED, "time": "O(n)", "space": "O(n)"},
    )
    assert passed.status_code == 200
    assert '<p class="outcome pass">' in passed.text
    assert "failed" not in passed.text
    # Every check in the hidden suite reached the verdict, so a green page is a
    # suite that ran rather than a suite that collected nothing.
    assert passed.text.count('class="check passed"') >= 5

    # The page a reload gives is the verdict the submission gave, because both
    # render `partials/verdict.html` over the same stored attempt.
    reloaded = client.get(second_url)
    assert reloaded.status_code == 200
    assert passed.text.strip() in reloaded.text

    # Nothing left behind: both attempts disposed of their own workspace, and the
    # attempt rows survive in a database that outlives the request.
    assert list((tmp_path / "ws").iterdir()) == []
    assert (tmp_path / "practice.db").is_file()
    assert "Nothing open" in client.get("/").text
