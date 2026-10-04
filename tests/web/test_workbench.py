"""`/attempt/{id}` — the page, in each of the states an attempt can be in."""

from __future__ import annotations

from typing import TYPE_CHECKING

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
