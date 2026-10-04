"""`/` — the due queue, the streak and the weakest tags.

The phase's exit criterion, at the surface that has to meet it: *"what should I
practice today?" is answered by the tool, not by you.* So the tests here are
about what the page offers rather than about markup — that the whole library is
offered before anything has been scheduled, that a scheduled exercise leaves and
comes back, and that a streak survives the night.

`tests/web/test_shell.py` keeps the layout and open-attempt assertions, which are
about the page every route is built on rather than about this one.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from practice.domain.ids import ExerciseId
from practice.interface.web.routes.dashboard import QUEUE_LIMIT
from tests.fakes import a_kata
from tests.unit.application.helpers import RecordingGrader, a_failing_verdict
from tests.web.conftest import a_wiring, client_for

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
SOLUTION = "def two_sum(values, target):\n    return (0, 1)\n"


def solve_and_schedule(client: TestClient, wiring: Wiring, grade: str = "good") -> None:
    """Start a kata, submit it, and press a grade — the whole loop, through HTTP.

    Through the app rather than through the stores, because what the dashboard
    reads is what the app wrote: a test that saved a card directly would pass
    with the review endpoint removed.
    """
    started = wiring.services.start_attempt(KATA)
    client.post(f"/api/attempt/{started.attempt.id}/submit", data={"source": SOLUTION})
    client.post(f"/api/attempt/{started.attempt.id}/review", data={"grade": grade})


# --- the due queue ---------------------------------------------------------


def test_an_unpractised_library_is_entirely_due(client: TestClient) -> None:
    """The state a fresh install is in, and the one where the question most needs
    answering. A dashboard built from the card table alone would say "nothing
    due" next to a library nobody has opened.
    """
    body = client.get("/").text

    assert "Due today" in body
    assert "Two Sum" in body
    assert "Revert a pushed commit" in body
    assert "One row per customer" in body
    # One "new" chip per never-attempted exercise -- all three of them, which
    # is also the smallest assertion that notices a kind being dropped from the
    # queue entirely.
    assert body.count('class="chip new"') == 3


def test_a_queue_row_can_be_started_from_the_dashboard(
    client: TestClient, wiring: Wiring
) -> None:
    """A list of things to do, not a count of them. The form is the browse
    page's, posting to the one route that provisions a workspace.
    """
    response = client.post(
        "/attempt", data={"exercise_id": str(KATA)}, follow_redirects=False
    )

    assert response.status_code == 303
    assert len(wiring.attempts) == 1


def test_an_exercise_with_an_open_attempt_offers_resume_instead_of_start(
    client: TestClient, wiring: Wiring
) -> None:
    """Starting a second attempt would provision a second workspace and split the
    budget across two attempts that look like one piece of work. The same join
    `/browse` makes, because the same mistake is available here.
    """
    started = wiring.services.start_attempt(KATA)

    body = client.get("/").text

    assert f'href="/attempt/{started.attempt.id}">Resume</a>' in body


def test_a_scheduled_exercise_leaves_the_queue(
    client: TestClient, wiring: Wiring
) -> None:
    solve_and_schedule(client, wiring)

    body = client.get("/").text

    assert "Two Sum" not in body.split("How it is going")[0]
    assert "Revert a pushed commit" in body


def test_it_comes_back_marked_overdue(client: TestClient, wiring: Wiring) -> None:
    """`FixedScheduler` pushes every card out three days, so four days on is a
    day overdue -- and the page says so in words rather than only in a colour.
    """
    solve_and_schedule(client, wiring)
    wiring.clock.advance(timedelta(days=4))

    body = client.get("/").text

    assert "1 day overdue" in body


def test_the_queue_is_cut_and_says_how_much_it_cut() -> None:
    """The cut is the page's decision and not the use case's: how much fits on a
    panel is a question about this page. It prints the total either way, so the
    cut never hides the size of what is waiting.
    """
    wiring = a_wiring()
    wiring.content.add(
        *(
            a_kata(exercise_id=f"katas/filler-{index}")
            for index in range(QUEUE_LIMIT + 2)
        )
    )

    with client_for(wiring) as crowded:
        body = crowded.get("/").text

    # Nothing is open, so every `li` on the page is a queue row.
    assert body.count("<li>") == QUEUE_LIMIT
    assert f"{QUEUE_LIMIT + 5} waiting in all" in body


def test_a_fully_scheduled_library_says_nothing_is_due(
    client: TestClient, wiring: Wiring
) -> None:
    """Which is a real state and a good one, so it reads as an achievement
    rather than as a page that failed to load.
    """
    for exercise_id in (
        "katas/two-sum",
        "git/revert-a-pushed-commit",
        "sql/one-row-per-customer",
    ):
        started = wiring.services.start_attempt(ExerciseId(exercise_id))
        client.post(
            f"/api/attempt/{started.attempt.id}/submit", data={"source": SOLUTION}
        )
        client.post(f"/api/attempt/{started.attempt.id}/review", data={})

    body = client.get("/").text

    assert "Nothing due" in body


# --- the streak and the weak tags ------------------------------------------


def test_nothing_graded_reports_no_streak_rather_than_zero(
    client: TestClient,
) -> None:
    body = client.get("/").text

    assert "No streak yet" in body
    assert "Nothing graded yet" in body


def test_one_attempt_today_starts_a_streak(client: TestClient, wiring: Wiring) -> None:
    solve_and_schedule(client, wiring)

    body = client.get("/").text

    assert "<strong>1 day</strong> running" in body
    assert "1 of 1 attempt" in body
    assert "1 exercise" in body


def test_a_streak_survives_the_night(client: TestClient, wiring: Wiring) -> None:
    """Counted back from yesterday when today has nothing yet. A counter that
    reset at midnight and came back that evening is one nobody would trust.
    """
    solve_and_schedule(client, wiring)
    wiring.clock.advance(timedelta(days=1))

    assert "<strong>1 day</strong> running" in client.get("/").text


def test_a_clean_record_offers_no_weakest_tags(
    client: TestClient, wiring: Wiring
) -> None:
    """The section disappears rather than listing your best tag as your worst."""
    solve_and_schedule(client, wiring)

    assert "Weakest tags" not in client.get("/").text


def test_a_failed_attempt_puts_its_tags_in_the_weak_list() -> None:
    """Its own wiring, because the grader has to be chosen before the client is
    built -- one swapped afterwards would make every test here order-dependent.
    """
    wiring = a_wiring(RecordingGrader(a_failing_verdict()))
    with client_for(wiring) as failing:
        solve_and_schedule(failing, wiring)
        body = failing.get("/").text

    assert "Weakest tags" in body
    assert "0/1 passed" in body
