"""`/attempt/{id}` — the page, in each of the states an attempt can be in."""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.attempt import AttemptMode
from practice.domain.exercise import KataSpec, SqlDrillSpec
from practice.domain.ids import ExerciseId

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")
DRILL = ExerciseId("sql/one-row-per-customer")

STUB = "def two_sum(values, target):\n    ...\n"
DRILL_STUB = "-- every customer and how many orders they have placed\n"


def test_the_workbench_shows_the_prompt(client: TestClient, wiring: Wiring) -> None:
    started = wiring.services.start_attempt(KATA)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert "Two Sum" in body
    assert "add up to the target" in body


def test_a_kata_opens_the_editor_on_its_stub(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)
    spec = started.exercise.spec
    assert isinstance(spec, KataSpec)
    wiring.provisioner.workspace_for(started.attempt.id).write_file(spec.stub, STUB)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert "def two_sum(values, target):" in body
    assert "/static/vendor/codemirror.min.js" in body
    assert "/static/vendor/codemirror-python.min.js" in body


def test_the_editor_mode_comes_from_the_exercise(
    client: TestClient, wiring: Wiring
) -> None:
    """From the spec's own language, not hardcoded.

    Which is the claim §15 question 3 rests on: a second language is a content
    change plus a vendored mode file, and nothing in the page.
    """
    started = wiring.services.start_attempt(KATA)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert 'mode: "python"' in body


def test_a_git_scenario_gets_a_console_rather_than_an_editor(
    client: TestClient, wiring: Wiring
) -> None:
    """One page, two right-hand panels, and the branch is in the template.

    The console's own behaviour is `tests/web/test_console.py`; what this asserts
    is the dispatch -- and that no editor machinery is loaded for a page that has
    no editor on it.
    """
    started = wiring.services.start_attempt(SCENARIO)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert "codemirror.min.js" not in body
    assert 'id="console-log"' in body


def test_a_finished_attempt_shows_its_verdict_instead_of_an_editor(
    client: TestClient, wiring: Wiring
) -> None:
    """The case `OpenWorkbench` exists for: a tab left open across a submission.

    `ResumeAttempt` refuses a finished attempt, correctly, and this URL still has
    to render — with the one thing a finished attempt has left to show.
    """
    started = wiring.services.start_attempt(KATA)
    wiring.services.submit_solution(started.attempt.id, source="def two_sum(): ...")

    response = client.get(f"/attempt/{started.attempt.id}")

    assert response.status_code == 200
    assert "Finds the two positions" in response.text
    assert "codemirror.min.js" not in response.text


def test_an_unknown_attempt_is_a_page_not_a_traceback(client: TestClient) -> None:
    response = client.get("/attempt/00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert "no attempt with id" in response.text


def test_a_malformed_id_is_a_404_rather_than_a_validation_error(
    client: TestClient,
) -> None:
    """A `UUID`-typed path parameter would answer 422 with a page about the shape
    of the string. Someone opening `/attempt/oops` wants to be told there is
    nothing there.
    """
    response = client.get("/attempt/oops")

    assert response.status_code == 404


def test_an_attempt_whose_workspace_was_collected_says_to_abandon_it(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)
    wiring.provisioner.collect(started.attempt.id)

    response = client.get(f"/attempt/{started.attempt.id}")

    assert response.status_code == 404
    assert "abandon it" in response.text


def test_an_attempt_whose_exercise_left_the_library_says_to_abandon_it(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)
    wiring.content.forget(KATA)

    response = client.get(f"/attempt/{started.attempt.id}")

    assert response.status_code == 404
    assert "no longer in the library" in response.text


def test_the_page_keeps_the_navigation_when_it_refuses(client: TestClient) -> None:
    """A refusal is a place to navigate away from, so it is rendered in the layout.

    A bare error page takes the navigation away at the moment it is most wanted.
    """
    body = client.get("/attempt/oops").text

    assert "swe-practice" in body
    assert 'href="/browse"' in body


def test_opening_the_workbench_records_nothing(
    client: TestClient, wiring: Wiring
) -> None:
    """A page load is not something the solver did in the exercise.

    The process assertions of §6.3 read the event log to decide whether someone
    reached for the reflog; an entry per page view would make every advisory
    check learn to ignore one kind of entry.
    """
    started = wiring.services.start_attempt(KATA)
    before = len(started.attempt.events)

    client.get(f"/attempt/{started.attempt.id}")
    client.get(f"/attempt/{started.attempt.id}")

    reloaded = wiring.attempts.get(started.attempt.id)
    assert reloaded is not None
    assert len(reloaded.events) == before


# --- which attempt is in front (ADR 0026) ----------------------------------


def test_loading_a_workbench_does_not_make_it_the_current_attempt(
    client: TestClient, wiring: Wiring
) -> None:
    """A page loaded is not a page looked at -- a link opened in a background
    tab must not take the mark from the attempt on screen -- and a GET here
    "cannot change anything", which is what the cross-origin guard rests on.
    """
    older = wiring.services.start_attempt(KATA)
    newer = wiring.services.start_attempt(SCENARIO)
    wiring.services.mark_current_attempt(newer.attempt.id)

    client.get(f"/attempt/{older.attempt.id}")

    assert wiring.attempts.current() == newer.attempt.id


def test_starting_from_the_browser_leaves_marking_to_the_page(
    client: TestClient, wiring: Wiring
) -> None:
    """The Start button redirects to the workbench, and the workbench says it
    is in front if it is. A start that marked would do so for a form submitted
    into a background tab too -- and is the write `practice solve` shares.
    """
    working_on = wiring.services.start_attempt(SCENARIO)
    wiring.services.mark_current_attempt(working_on.attempt.id)

    client.post("/attempt", data={"exercise_id": str(KATA)}, follow_redirects=False)

    assert len(wiring.services.list_open_attempts()) == 2
    assert wiring.attempts.current() == working_on.attempt.id


def test_a_tab_coming_to_the_front_makes_its_attempt_the_current_one(
    client: TestClient, wiring: Wiring
) -> None:
    """The two-tab case. Switching tabs loads nothing, so the page says so."""
    older = wiring.services.start_attempt(KATA)
    newer = wiring.services.start_attempt(SCENARIO)
    wiring.services.mark_current_attempt(newer.attempt.id)

    response = client.post(f"/api/attempt/{older.attempt.id}/current")

    assert response.status_code == 204
    assert response.content == b""
    assert wiring.attempts.current() == older.attempt.id


def test_an_open_workbench_carries_the_script_and_its_own_attempts_endpoint(
    client: TestClient, wiring: Wiring
) -> None:
    """The page's half: the tag is there and the URL on it is the one the
    route is declared with. What the script *does* with it is
    `test_in_front_script.py`'s, which runs the file this serves.
    """
    started = wiring.services.start_attempt(KATA)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert (
        '<script src="/static/in-front.js" '
        f'data-current-url="/api/attempt/{started.attempt.id}/current"></script>'
    ) in body
    assert client.get("/static/in-front.js").status_code == 200


def test_a_finished_attempt_cannot_take_the_mark(
    client: TestClient, wiring: Wiring
) -> None:
    """A tab left open across a submission goes on reporting that it came to
    the front. It is refused -- which is what tells the script to stop -- and
    its page is no longer drawn with the script at all.
    """
    finished = wiring.services.start_attempt(KATA)
    wiring.services.submit_solution(finished.attempt.id, source="def two_sum(): ...")
    working_on = wiring.services.start_attempt(SCENARIO)
    wiring.services.mark_current_attempt(working_on.attempt.id)

    response = client.post(f"/api/attempt/{finished.attempt.id}/current")

    assert response.status_code == 409
    assert wiring.attempts.current() == working_on.attempt.id
    assert "in-front.js" not in client.get(f"/attempt/{finished.attempt.id}").text


def test_reporting_an_attempt_that_does_not_exist_is_a_404(client: TestClient) -> None:
    unknown = client.post("/api/attempt/00000000-0000-4000-8000-000000000000/current")
    malformed = client.post("/api/attempt/oops/current")

    assert unknown.status_code == 404
    assert malformed.status_code == 404


# --- the third kind's workbench -------------------------------------------


def test_a_drill_opens_the_editor_on_its_stub(
    client: TestClient, wiring: Wiring
) -> None:
    """The page a drill gets, and the reason `editable_source` exists.

    Before Phase 14 this route asked `isinstance(spec, KataSpec)` to decide
    whether to draw an editor at all, so a drill would have been served a
    console over a repository it does not have.
    """
    started = wiring.services.start_attempt(DRILL)
    spec = started.exercise.spec
    assert isinstance(spec, SqlDrillSpec)
    wiring.provisioner.workspace_for(started.attempt.id).write_file(
        spec.stub, DRILL_STUB
    )

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert "every customer and how many orders" in body
    assert "/static/vendor/codemirror.min.js" in body


def test_a_drill_loads_the_sql_mode_and_not_the_python_one(
    client: TestClient, wiring: Wiring
) -> None:
    """**The half of §15 Q3's prediction that was wrong.**

    `vendor.py` said a second language costs "a second line here and nothing
    else". The second line is right; this page had
    `codemirror-python.min.js` written into its script tag, so a drill would
    have loaded a Python tokenizer and then asked CodeMirror for a `sql` mode
    it had not loaded — which fails by silently giving you a plain textarea,
    the worst available way for it to fail. No existing assertion could have
    caught it: the mode *name* was already coming from the spec.
    """
    started = wiring.services.start_attempt(DRILL)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert 'mode: "sql"' in body
    assert "/static/vendor/codemirror-sql.min.js" in body
    assert "/static/vendor/codemirror-python.min.js" not in body


def test_a_drill_gets_no_repository_panel(client: TestClient, wiring: Wiring) -> None:
    """The other half of the same split. `InspectRepository` *refuses* anything
    that is not a scenario, so the page must not ask — and the branch that
    decides used to be "is this a kata", which a drill is not.
    """
    started = wiring.services.start_attempt(DRILL)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert "Repository state" not in body


# --- interview mode ---------------------------------------------------------


def test_an_interview_workbench_says_so_and_states_the_clock(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA, mode=AttemptMode.INTERVIEW)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert "Interview conditions" in body
    assert "interview" in body
    assert "minutes left of" in body
    assert "Reload to check again" in body


def test_an_interview_workbench_draws_no_hint_panel(
    client: TestClient, wiring: Wiring
) -> None:
    """Nothing in the template had to learn about the mode for this: the panel
    is drawn on `hint_count`, and the policy was built with no hints.
    """
    interview = wiring.services.start_attempt(KATA, mode=AttemptMode.INTERVIEW)
    practice = wiring.services.start_attempt(SCENARIO)

    withheld = client.get(f"/attempt/{interview.attempt.id}").text
    offered = client.get(f"/attempt/{practice.attempt.id}").text

    assert 'id="hint-list"' not in withheld
    assert "Reveal a hint" not in withheld
    assert 'id="hint-list"' in offered


def test_an_interview_workbench_offers_no_own_editor_button(
    client: TestClient, wiring: Wiring
) -> None:
    """The control is withdrawn rather than left to post and be refused. A
    button whose only job is to explain that it does not work is worse than no
    button.
    """
    interview = wiring.services.start_attempt(KATA, mode=AttemptMode.INTERVIEW)
    practice = wiring.services.start_attempt(KATA)

    withheld = client.get(f"/attempt/{interview.attempt.id}").text
    offered = client.get(f"/attempt/{practice.attempt.id}").text

    assert 'id="open-editor"' not in withheld
    assert 'id="open-editor"' in offered


def test_an_interview_workbench_still_has_its_editor_and_submit(
    client: TestClient, wiring: Wiring
) -> None:
    """What interview mode must *not* take away. Withdrawing the workspace path
    is only honest if there is still a way to answer.
    """
    started = wiring.services.start_attempt(KATA, mode=AttemptMode.INTERVIEW)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert 'id="source"' in body
    assert 'id="solution-form"' in body


def test_a_practice_workbench_says_nothing_about_interviews(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert "Interview conditions" not in body
    assert "minutes left of" not in body


def test_the_start_form_offers_the_mode_and_defaults_to_practice(
    client: TestClient,
) -> None:
    """The checkbox is on the form that opens the attempt, because that is the
    only moment the mode can be chosen.
    """
    page = client.get("/browse").text

    assert 'name="interview"' in page
    assert 'value="1"' in page


def test_starting_without_the_box_ticked_is_a_practice_run(
    client: TestClient, wiring: Wiring
) -> None:
    """An unchecked box sends nothing, which is what makes practice the answer
    for a form that has never heard of the field.
    """
    client.post("/attempt", data={"exercise_id": str(KATA)}, follow_redirects=False)

    opened = wiring.services.list_open_attempts()
    assert len(opened) == 1
    assert opened[0].attempt.policy.is_interview is False


def test_starting_with_the_box_ticked_opens_an_interview(
    client: TestClient, wiring: Wiring
) -> None:
    client.post(
        "/attempt",
        data={"exercise_id": str(KATA), "interview": "1"},
        follow_redirects=False,
    )

    opened = wiring.services.list_open_attempts()
    assert len(opened) == 1
    assert opened[0].attempt.policy.is_interview is True


def test_the_hint_endpoint_refuses_an_interview_outright(
    client: TestClient, wiring: Wiring
) -> None:
    """What makes the missing button a withdrawal rather than a hidden control.

    The sentence is the aggregate's, not this layer's: `reveal_next_hint` is the
    only place it is written, and it says interview mode is withholding them
    rather than that the exercise has none -- which was the one thing Phase 15's
    first commit had to change about an existing message.
    """
    started = wiring.services.start_attempt(KATA, mode=AttemptMode.INTERVIEW)

    response = client.post(f"/api/attempt/{started.attempt.id}/hint")

    assert "interview mode withholds" in response.text
    assert "this exercise has 0" not in response.text
