"""Tracks, the Next button under a verdict, and "done, and when" on every list.

Three things one phase added to the web app, tested together because they are
one behaviour seen from three pages: the attempt log is asked *per exercise*,
and the answer is shown wherever an exercise is listed.

The assertions that matter most are the ones about what is **carried**. A
track's name travels from the page an attempt is started on, through the
redirect, into the two submit forms and back out in the Next button -- five
hops with no stored state behind them, so a hop that dropped it would leave a
page that works and a Next button that silently follows the wrong track.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.domain.ids import ExerciseId
from practice.domain.track import Track
from tests.unit.application.helpers import RecordingGrader, a_failing_verdict
from tests.web.conftest import a_wiring, client_for

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi.testclient import TestClient

    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")
DRILL = ExerciseId("sql/one-row-per-customer")
SOLUTION = "def two_sum(values, target):\n    return (0, 1)\n"

#: Declared first, so it is the default: every exercise, in the fake's order.
EVERYTHING = Track(
    name="everything",
    title="The whole library",
    summary="All three, one after another.",
    exercises=(SCENARIO, KATA, DRILL),
)

#: Declared second and in a different order, so a test can tell which track a
#: Next button followed: after the kata comes the *scenario* here and the
#: *drill* on the default.
KATA_FIRST = Track(
    name="kata-first",
    title="Kata first",
    summary="The kata, then the git scenario.",
    exercises=(KATA, SCENARIO),
)


def with_tracks(wiring: Wiring) -> Wiring:
    wiring.content.offer(EVERYTHING, KATA_FIRST)
    return wiring


@pytest.fixture
def wiring() -> Wiring:
    return with_tracks(a_wiring())


def solve(client: TestClient, wiring: Wiring, exercise_id: ExerciseId = KATA) -> str:
    """Start and submit through the app. The default grader passes everything."""
    started = wiring.services.start_attempt(exercise_id)
    client.post(f"/api/attempt/{started.attempt.id}/submit", data={"source": SOLUTION})
    return str(started.attempt.id)


@pytest.fixture
def failing() -> Iterator[tuple[TestClient, Wiring]]:
    """The same app over a grader that fails everything."""
    wiring = with_tracks(a_wiring(grader=RecordingGrader(a_failing_verdict())))
    with client_for(wiring) as client:
        yield client, wiring


# --- the two pages -------------------------------------------------------------


def test_the_layout_links_to_the_tracks(client: TestClient) -> None:
    assert '<a href="/tracks">Tracks</a>' in client.get("/").text


def test_the_listing_shows_every_track_and_how_far_along_it_is(
    client: TestClient, wiring: Wiring
) -> None:
    solve(client, wiring)

    page = client.get("/tracks").text

    assert 'href="/tracks/everything"' in page
    assert 'href="/tracks/kata-first"' in page
    assert "1 of 3 done" in page
    assert "1 of 2 done" in page
    assert '<progress value="1" max="3">' in page


def test_a_track_nobody_has_started_offers_start_and_one_in_progress_continue(
    client: TestClient, wiring: Wiring
) -> None:
    assert ">Start</button>" in client.get("/tracks").text

    solve(client, wiring)

    assert ">Continue</button>" in client.get("/tracks").text


def test_the_listing_says_so_when_the_library_declares_no_tracks() -> None:
    with client_for(a_wiring()) as client:
        page = client.get("/tracks")

    assert page.status_code == 200
    assert "This library declares no tracks" in page.text


def test_a_track_lists_its_steps_numbered_in_its_own_order(client: TestClient) -> None:
    page = client.get("/tracks/kata-first").text

    assert "<h1>Kata first</h1>" in page
    assert "The kata, then the git scenario." in page
    assert page.index('<span class="step-number">1.</span> Two Sum') < page.index(
        '<span class="step-number">2.</span> Revert a pushed commit'
    )


def test_every_start_on_a_track_posts_the_tracks_name(client: TestClient) -> None:
    """The one thing these pages do that Browse does not, and the first hop."""
    page = client.get("/tracks/kata-first").text

    assert page.count('<input type="hidden" name="track" value="kata-first">') == 3


def test_a_finished_step_says_when_and_can_still_be_started(
    client: TestClient, wiring: Wiring
) -> None:
    """A track records where you are; it does not lock what is behind you."""
    solve(client, wiring)
    today = wiring.clock.now().date().isoformat()

    page = client.get("/tracks/kata-first").text

    assert f"passed {today}" in page
    assert "Continue with step 2: Revert a pushed commit" in page
    assert f'name="exercise_id" value="{KATA}"' in page


def test_a_step_with_an_attempt_open_is_offered_as_resume(
    client: TestClient, wiring: Wiring
) -> None:
    """A second Start would provision a second workspace for one piece of work."""
    started = wiring.services.start_attempt(KATA)

    page = client.get("/tracks/kata-first").text

    assert f'href="/attempt/{started.attempt.id}?track=kata-first"' in page
    assert "Resume step 1: Two Sum" in page


def test_a_track_with_every_step_passed_says_so(
    client: TestClient, wiring: Wiring
) -> None:
    solve(client, wiring, KATA)
    solve(client, wiring, SCENARIO)

    assert "Every step passed." in client.get("/tracks/kata-first").text
    assert '<span class="chip done">finished</span>' in client.get("/tracks").text


def test_an_unknown_track_is_a_404_with_the_navigation_still_on_it(
    client: TestClient,
) -> None:
    page = client.get("/tracks/renamed-since")

    assert page.status_code == 404
    assert "No such track" in page.text
    assert '<a href="/tracks">Tracks</a>' in page.text


# --- carrying the track --------------------------------------------------------


def test_starting_from_a_track_puts_its_name_in_the_workbench_url(
    client: TestClient,
) -> None:
    response = client.post(
        "/attempt",
        data={"exercise_id": str(KATA), "track": "kata-first"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith("?track=kata-first")


def test_starting_without_a_track_leaves_the_url_bare(client: TestClient) -> None:
    """Browse and the due queue send no field at all, which reads as no track."""
    response = client.post(
        "/attempt", data={"exercise_id": str(KATA)}, follow_redirects=False
    )

    assert "?" not in response.headers["location"]


def test_a_track_the_library_does_not_declare_is_dropped_not_refused(
    client: TestClient,
) -> None:
    """A stale link kept past a rename costs the track, not the attempt."""
    response = client.post(
        "/attempt",
        data={"exercise_id": str(KATA), "track": "renamed-since"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "?" not in response.headers["location"]


def test_the_kata_workbench_posts_the_track_back_with_the_solution(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)

    with_track = client.get(f"/attempt/{started.attempt.id}?track=kata-first").text
    without = client.get(f"/attempt/{started.attempt.id}").text

    assert 'track: "kata-first"' in with_track
    assert 'track: ""' in without


def test_the_scenario_workbench_posts_the_track_back_with_the_submission(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(SCENARIO)
    field = '<input type="hidden" name="track" value="kata-first">'

    assert field in client.get(f"/attempt/{started.attempt.id}?track=kata-first").text
    assert 'name="track"' not in client.get(f"/attempt/{started.attempt.id}").text


def test_a_track_name_in_the_url_that_names_nothing_is_not_echoed(
    client: TestClient, wiring: Wiring
) -> None:
    """The query string is somebody else's text until it has matched a track."""
    started = wiring.services.start_attempt(KATA)

    page = client.get(f"/attempt/{started.attempt.id}?track=%22%3E%3Cb%3E").text

    assert 'track: ""' in page
    assert "<b>" not in page


# --- the Next button -----------------------------------------------------------


def test_a_kata_submission_offers_the_next_step_on_its_track(
    client: TestClient, wiring: Wiring
) -> None:
    """After the kata comes the scenario on `kata-first` and the drill on the
    default, so the title says which track was followed.
    """
    started = wiring.services.start_attempt(KATA)

    fragment = client.post(
        f"/api/attempt/{started.attempt.id}/submit",
        data={"source": SOLUTION, "track": "kata-first"},
    ).text

    assert 'id="next"' in fragment
    assert "Next: Revert a pushed commit" in fragment
    assert f'name="exercise_id" value="{SCENARIO}"' in fragment
    assert '<input type="hidden" name="track" value="kata-first">' in fragment
    assert "Step 2 of 2 on" in fragment
    assert "1 done" in fragment


def test_with_no_track_the_next_step_follows_the_first_one_declared(
    client: TestClient, wiring: Wiring
) -> None:
    """An attempt started from Browse. The same kata, and a different next."""
    started = wiring.services.start_attempt(KATA)

    fragment = client.post(
        f"/api/attempt/{started.attempt.id}/submit", data={"source": SOLUTION}
    ).text

    assert "Next: One row per customer" in fragment
    assert '<input type="hidden" name="track" value="everything">' in fragment


def test_a_scenario_submission_offers_the_next_step_too(
    client: TestClient, wiring: Wiring
) -> None:
    """Where to go next belongs to the attempt and not to the exercise kind,
    which is why both submit routes build the same block.
    """
    started = wiring.services.start_attempt(SCENARIO)

    fragment = client.post(
        f"/api/attempt/{started.attempt.id}/submit-scenario",
        data={"track": "kata-first"},
    ).text

    assert "Next: Two Sum" in fragment
    assert '<input type="hidden" name="track" value="kata-first">' in fragment


def test_the_next_step_is_there_before_any_schedule_grade_is_pressed(
    client: TestClient, wiring: Wiring
) -> None:
    """The complaint this answers: the only way on used to be a link that
    appeared inside the schedule block *after* grading. Both blocks are in one
    response now, and the Next block is outside `#review` -- which that
    endpoint replaces whole.
    """
    started = wiring.services.start_attempt(KATA)

    fragment = client.post(
        f"/api/attempt/{started.attempt.id}/submit", data={"source": SOLUTION}
    ).text

    assert "Suggested" in fragment
    # Nested, there would be no closing tag between the two ids: `#review`
    # would still be open when `#next` began, and a grade would swap it away.
    between = fragment[fragment.index('id="review"') : fragment.index('id="next"')]
    assert "</section>" in between


def test_reloading_a_finished_attempt_shows_the_same_next_step(
    client: TestClient, wiring: Wiring
) -> None:
    """One partial for the fragment and the page, so a reload shows what the
    submission showed -- on the track in the URL.
    """
    attempt_id = solve(client, wiring)

    page = client.get(f"/attempt/{attempt_id}?track=kata-first").text

    assert "Next: Revert a pushed commit" in page
    assert '<input type="hidden" name="track" value="kata-first">' in page


def test_a_passed_attempt_is_not_offered_a_retry(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = solve(client, wiring)

    assert "Try this one again" not in client.get(f"/attempt/{attempt_id}").text


def test_a_failed_attempt_is_offered_a_retry_and_the_step_after(
    failing: tuple[TestClient, Wiring],
) -> None:
    """Moving on is as likely as trying again, so both are there -- and Next is
    the step *after* the one that failed, not the same one handed back.
    """
    client, wiring = failing
    started = wiring.services.start_attempt(KATA)

    fragment = client.post(
        f"/api/attempt/{started.attempt.id}/submit",
        data={"source": SOLUTION, "track": "kata-first"},
    ).text

    assert "Next: Revert a pushed commit" in fragment
    assert "Try this one again" in fragment
    retry = fragment[fragment.index("Try this one again") - 400 :]
    assert f'name="exercise_id" value="{KATA}"' in retry
    assert "0 done" in fragment


def test_the_last_unfinished_step_says_the_track_has_run_out(
    client: TestClient, wiring: Wiring
) -> None:
    solve(client, wiring, KATA)
    started = wiring.services.start_attempt(SCENARIO)

    fragment = client.post(
        f"/api/attempt/{started.attempt.id}/submit-scenario",
        data={"track": "kata-first"},
    ).text

    assert "Nothing else is unfinished on" in fragment
    assert "2 of 2 done" in fragment
    assert "Next:" not in fragment
    assert 'href="/tracks"' in fragment


def test_a_next_step_with_an_attempt_already_open_is_a_resume_link(
    client: TestClient, wiring: Wiring
) -> None:
    waiting = wiring.services.start_attempt(SCENARIO)
    started = wiring.services.start_attempt(KATA)

    fragment = client.post(
        f"/api/attempt/{started.attempt.id}/submit",
        data={"source": SOLUTION, "track": "kata-first"},
    ).text

    assert f'href="/attempt/{waiting.attempt.id}?track=kata-first"' in fragment
    assert "Resume: Revert a pushed commit" in fragment
    assert "Next:" not in fragment


def test_a_library_with_no_tracks_has_no_next_block() -> None:
    """No route to be on. The schedule block's own link is still the way out."""
    wiring = a_wiring()
    with client_for(wiring) as client:
        started = wiring.services.start_attempt(KATA)
        fragment = client.post(
            f"/api/attempt/{started.attempt.id}/submit", data={"source": SOLUTION}
        ).text
        page = client.get(f"/attempt/{started.attempt.id}").text

    assert 'id="review"' in fragment
    assert 'id="next"' not in fragment
    assert 'id="next"' not in page


def test_an_open_attempt_has_no_next_block(client: TestClient, wiring: Wiring) -> None:
    started = wiring.services.start_attempt(KATA)

    assert 'id="next"' not in client.get(f"/attempt/{started.attempt.id}").text


# --- done, and when ------------------------------------------------------------


def test_browse_says_nothing_about_an_exercise_never_attempted(
    client: TestClient,
) -> None:
    """The absence is the state: a hundred "not started" chips mean nothing."""
    page = client.get("/browse").text

    assert "chip done" not in page
    assert "chip tried" not in page


def test_browse_says_when_an_exercise_was_passed(
    client: TestClient, wiring: Wiring
) -> None:
    """*Which have I done and when*, on the list it is a question about. The
    exercise was never scheduled -- nothing here presses a grade -- and it is
    marked done anyway, because the attempt log is what is asked.
    """
    solve(client, wiring)
    today = wiring.clock.now().date().isoformat()

    page = client.get("/browse").text

    assert page.count(f'<span class="chip done">passed {today}</span>') == 1


def test_browse_marks_an_exercise_tried_and_not_passed(
    failing: tuple[TestClient, Wiring],
) -> None:
    client, wiring = failing
    solve(client, wiring)
    today = wiring.clock.now().date().isoformat()

    page = client.get("/browse").text

    assert f"not passed yet · tried {today}" in page
    assert "chip done" not in page


def test_browse_counts_repeat_attempts(client: TestClient, wiring: Wiring) -> None:
    solve(client, wiring)
    assert "attempts</span>" not in client.get("/browse").text

    solve(client, wiring)

    assert '<span class="chip">2 attempts</span>' in client.get("/browse").text


def test_the_queue_no_longer_calls_a_solved_exercise_new(
    client: TestClient, wiring: Wiring
) -> None:
    """**The tool forgetting, as it looked.** No card exists until a schedule
    grade is pressed, so the queue's own answer for this exercise is still "no
    card" -- and that used to be printed as *new* beside an exercise passed a
    minute ago.
    """
    assert client.get("/").text.count('<span class="chip new">new</span>') == 3

    solve(client, wiring)
    today = wiring.clock.now().date().isoformat()

    page = client.get("/").text

    assert page.count('<span class="chip new">new</span>') == 2
    assert "never scheduled" in page
    assert f"passed {today}" in page


def test_the_dashboard_offers_each_track_with_a_way_into_it(
    client: TestClient, wiring: Wiring
) -> None:
    solve(client, wiring)

    page = client.get("/").text

    assert "<h2>Tracks</h2>" in page
    assert 'href="/tracks/kata-first"' in page
    assert "1 of 2 done · next: Revert a pushed commit" in page
    assert '<input type="hidden" name="track" value="kata-first">' in page
