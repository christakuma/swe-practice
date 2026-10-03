"""One exercise, graded and scheduled, and a dashboard that changes. Phase 9's exit.

PLAN.md §11 states it as a sentence rather than a feature: *"'what should I
practice today?' is answered by the tool, not by you."* This is the whole of that
loop over real adapters — the filesystem library, the subprocess provisioner, a
real pytest run and a real SQLite file — with nothing standing in for a browser
but the test client, which has to speak the request a browser sends because
`SameOriginMiddleware` refuses anything that does not.

**One test, like its Phase 7 and 8 siblings**, and for the same reason: it costs
a pytest subprocess and a provisioned workspace, and §9's rule is that anything
assertable one layer down belongs one layer down. The suggestion rule, the SM-2
arithmetic, the queue's ordering and every fragment are covered in milliseconds
in `tests/unit/` and `tests/web/`. What only this layer can show is that the
pieces compose across four requests and two stores: a verdict produced by a real
pytest run is read by the suggestion rule, the grade it proposes moves a card in
a real database, and the dashboard that asked the question stops asking it.

**The clock is the real one.** A `FakeClock` would let this test advance a day
and watch the card come due, which is the one thing it cannot show — and that is
the right trade: `tests/web/test_dashboard.py` makes a card come back overdue in
a millisecond, and what cannot be faked is that today's date, written by SQLite
and read back through the mapper, is the one the queue compares against.
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

ORIGIN = "http://127.0.0.1"
BROWSER = {"origin": ORIGIN, "sec-fetch-site": "same-origin"}

#: The one-pass dict, with the complexity the exercise expects. Declared on the
#: submission so the attempt passes *clean* -- no advisory, no hints, inside the
#: estimate -- which is the only input that produces `easy` and is therefore the
#: only one that proves the suggestion read the verdict rather than guessed.
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


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    """The real object graph over disposable storage, and the real library.

    The real content root deliberately: this is the test that should break if a
    shipped exercise stops being solvable and schedulable through the web app,
    which is the question `tests/web/` does not ask.
    """
    services = build_services(
        content=content_root(),
        workspaces=tmp_path / "ws",
        database=tmp_path / "practice.db",
    )
    with TestClient(create_app(services), base_url=ORIGIN, headers=BROWSER) as client:
        yield client


def test_the_tool_says_what_to_practise_and_stops_saying_it(
    client: TestClient, tmp_path: Path
) -> None:
    """Ask, solve, schedule, and ask again.

    The assertion that carries the phase is the last one: the exercise that was
    offered at the top of the page is not offered any more, and the thing that
    removed it is a card in a database written by a grade the tool proposed.
    """
    # Nothing has ever been practised, so the question has the answer it has to
    # have on a fresh install: everything. A queue built from the card table
    # alone would say "nothing due" beside an untouched library.
    opening = client.get("/")
    assert opening.status_code == 200
    assert "Due today" in opening.text
    assert "Two Sum" in opening.text
    assert "No streak yet" in opening.text

    started = client.post(
        "/attempt", data={"exercise_id": TWO_SUM}, follow_redirects=False
    )
    assert started.status_code == 303
    attempt_id = started.headers["location"].removeprefix("/attempt/")

    graded = client.post(
        f"/api/attempt/{attempt_id}/submit",
        data={"source": SOLVED, "time": "O(n)", "space": "O(n)"},
    )
    assert graded.status_code == 200
    assert '<p class="outcome pass">' in graded.text

    # The verdict comes back with the schedule control, in one response: the
    # suggestion is read off the attempt that just finished -- a clean pass, no
    # hints, well inside the estimate -- and that is `easy`.
    assert 'id="review"' in graded.text
    assert "<strong>easy</strong>" in graded.text
    assert "passed clean, inside the estimate, no hints" in graded.text

    # No grade in the body, which is how a solver takes the tool's reading.
    scheduled = client.post(f"/api/attempt/{attempt_id}/review", data={})
    assert scheduled.status_code == 200
    assert "Scheduled as <strong>easy</strong>" in scheduled.text
    # SM-2's first `EASY` step: four days, not the one-day learning step. Pinned
    # here because this is the only test in which the real scheduler, the real
    # mapper and the real `date` column all have to agree about one number.
    assert "in 4 days" in scheduled.text

    # Asked again, the tool has changed its answer -- which is the whole phase.
    after = client.get("/")
    assert "Two Sum" not in after.text.split("How it is going")[0]
    assert "<strong>1 day</strong> running" in after.text
    assert "1 of 1 attempt passed, 1 exercise scheduled" in after.text

    # And the card is on disk rather than in the process that wrote it, which is
    # the Phase 6 claim this phase is built on top of.
    assert (tmp_path / "practice.db").is_file()
    progress = client.get("/progress")
    assert "1 graded attempt, 1 passed (100%)" in progress.text
    assert "arrays" in progress.text

    # A second press is refused rather than advancing the interval twice for one
    # piece of evidence -- the double-click, over real storage.
    again = client.post(f"/api/attempt/{attempt_id}/review", data={"grade": "again"})
    assert "already been reviewed" in again.text

    # And the page agrees with the refusal before it is pressed: both read
    # `ReviewOffer.already_reviewed`, so what is offered and what is accepted
    # cannot come apart.
    reloaded = client.get(f"/attempt/{attempt_id}")
    assert "Already scheduled" in reloaded.text
    assert "<strong>easy</strong>" not in reloaded.text
