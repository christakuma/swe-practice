"""Choosing a step on a track, the finish-by goal, and the review switch.

One file because they came from one request: a person who wanted to pick any
step of a long track and stop being nagged by due dates.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from practice.domain.ids import ExerciseId
from practice.domain.track import Track
from tests.web.conftest import a_wiring, client_for, submit_to_the_end

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi.testclient import TestClient

    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")
DRILL = ExerciseId("sql/one-row-per-customer")

EVERYTHING = Track(
    name="everything",
    title="The whole library",
    summary="All three, one after another.",
    exercises=(SCENARIO, KATA, DRILL),
)


@pytest.fixture
def wiring() -> Wiring:
    made = a_wiring()
    made.content.offer(EVERYTHING)
    return made


@pytest.fixture
def client(wiring: Wiring) -> Iterator[TestClient]:
    with client_for(wiring) as found:
        yield found


def pass_the_kata(client: TestClient, wiring: Wiring) -> str:
    started = wiring.services.start_attempt(KATA)
    return submit_to_the_end(client, wiring, started.attempt.id, {"source": "x = 1\n"})


# --- choosing ---------------------------------------------------------------


def test_the_listing_says_the_title_opens_a_list_of_steps(client: TestClient) -> None:
    assert "choose a step (3)" in client.get("/tracks").text


def test_the_dashboard_says_it_too(client: TestClient) -> None:
    assert "choose a step (3)" in client.get("/").text


def test_every_step_is_a_row_with_its_own_start(client: TestClient) -> None:
    page = client.get("/tracks/everything").text

    for step in (SCENARIO, KATA, DRILL):
        assert f'value="{step}"' in page
    assert 'id="step-2"' in page
    assert "showing 3 of 3" in page


def test_a_search_narrows_the_list_and_keeps_numbers(client: TestClient) -> None:
    page = client.get("/tracks/everything", params={"q": "two-sum"}).text

    assert "showing 1 of 3" in page
    assert 'id="step-2"' in page
    assert 'id="step-1"' not in page


def test_a_search_with_no_match_says_so(client: TestClient) -> None:
    assert (
        "No step matches"
        in client.get("/tracks/everything", params={"q": "zzzzzz"}).text
    )


def test_the_status_filter_hides_what_is_done(
    client: TestClient, wiring: Wiring
) -> None:
    pass_the_kata(client, wiring)

    page = client.get("/tracks/everything", params={"show": "todo"}).text

    assert "showing 2 of 3" in page
    assert 'id="step-2"' not in page


# --- goals ------------------------------------------------------------------


def test_with_no_history_the_page_offers_a_date_and_projects_none(
    client: TestClient,
) -> None:
    page = client.get("/tracks/everything").text

    assert "Pass a few more steps" in page
    assert "At your recent pace" not in page


def test_a_goal_can_be_set_shown_and_cleared(
    client: TestClient, wiring: Wiring
) -> None:
    target = (wiring.clock.today() + timedelta(days=30)).isoformat()

    posted = client.post(
        "/tracks/everything/goal", data={"target_on": target}, follow_redirects=False
    )
    assert posted.status_code == 303
    page = client.get("/tracks/everything").text
    assert f"finish by {target}" in page
    assert "30 days left" in page

    client.post("/tracks/everything/goal/clear", follow_redirects=False)
    assert "Goal: finish by" not in client.get("/tracks/everything").text


def test_a_goal_in_the_past_is_refused(client: TestClient, wiring: Wiring) -> None:
    yesterday = (wiring.clock.today() - timedelta(days=1)).isoformat()

    refused = client.post("/tracks/everything/goal", data={"target_on": yesterday})

    assert refused.status_code == 422
    assert "day after today" in refused.text


def test_a_goal_that_is_not_a_date_is_refused(client: TestClient) -> None:
    refused = client.post("/tracks/everything/goal", data={"target_on": "soon"})

    assert refused.status_code == 422
    assert "YYYY-MM-DD" in refused.text


def test_a_blank_goal_with_no_pace_is_refused_rather_than_invented(
    client: TestClient,
) -> None:
    refused = client.post("/tracks/everything/goal", data={"target_on": ""})

    assert refused.status_code == 422
    assert "no pace to project" in refused.text


def test_a_goal_on_an_unknown_track_is_a_404(client: TestClient) -> None:
    assert client.post("/tracks/nope/goal", data={"target_on": ""}).status_code == 404
    assert client.post("/tracks/nope/goal/clear").status_code == 404


def test_a_goal_past_its_day_offers_a_replan(
    client: TestClient, wiring: Wiring
) -> None:
    target = (wiring.clock.today() + timedelta(days=1)).isoformat()
    client.post("/tracks/everything/goal", data={"target_on": target})
    wiring.clock.advance(timedelta(days=5))

    page = client.get("/tracks/everything").text

    assert "That day has passed" in page
    assert "Move goal" in page
    assert "Re-plan" not in page  # no pace to re-plan from, so not offered


def test_a_goal_due_today_is_not_called_passed(
    client: TestClient, wiring: Wiring
) -> None:
    target = (wiring.clock.today() + timedelta(days=1)).isoformat()
    client.post("/tracks/everything/goal", data={"target_on": target})
    wiring.clock.advance(timedelta(days=1))

    page = client.get("/tracks/everything").text

    assert "Today is the day" in page
    assert "That day has passed" not in page


def test_an_overdue_goal_can_be_moved_to_a_typed_date(
    client: TestClient, wiring: Wiring
) -> None:
    target = (wiring.clock.today() + timedelta(days=1)).isoformat()
    client.post("/tracks/everything/goal", data={"target_on": target})
    wiring.clock.advance(timedelta(days=5))

    assert "Move goal" in client.get("/tracks/everything").text


# --- the switch -------------------------------------------------------------


def test_scheduling_is_on_by_default(client: TestClient) -> None:
    page = client.get("/").text

    assert "Due today" in page
    assert "Turn off review scheduling" in page


def test_turning_it_off_hides_the_queue_and_back_on_restores_it(
    client: TestClient,
) -> None:
    client.post("/settings/reviews", data={"enabled": "0"}, follow_redirects=False)
    off = client.get("/").text
    assert "Due today" not in off
    assert "Turn on review scheduling" in off

    client.post("/settings/reviews", data={"enabled": "1"}, follow_redirects=False)
    assert "Due today" in client.get("/").text


def test_with_it_off_a_graded_attempt_has_no_schedule_panel(
    client: TestClient, wiring: Wiring
) -> None:
    assert 'id="review"' in pass_the_kata(client, wiring)

    client.post("/settings/reviews", data={"enabled": "0"})
    started = wiring.services.start_attempt(DRILL)
    off = submit_to_the_end(client, wiring, started.attempt.id, {"source": "x = 1\n"})

    assert 'id="review"' not in off
    assert 'href="/">Back to the dashboard' in off
