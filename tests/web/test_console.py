"""The git scenario console: running a line, appending it, and submitting.

Over fakes, like the rest of `tests/web/`: what a route gets wrong is which use
case it calls, what it hands the template, and what it does with a refusal — and
none of those needs a git process to be wrong in. The one test that drives a real
repository through these endpoints is the end-to-end one.

**Fragments are asserted as fragments.** A command response is an `<li>` and an
out-of-band `<p>`, not a page, so these tests check it has no `<html>` around it:
a route that accidentally rendered the layout would be swapped into the transcript
whole, and every assertion about the entry's contents would still pass.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.attempt import CommandResult
from practice.domain.ids import ExerciseId

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from practice.domain.ids import AttemptId
    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")


def a_scenario_attempt(wiring: Wiring) -> AttemptId:
    return wiring.services.start_attempt(SCENARIO).attempt.id


def run(client: TestClient, attempt_id: AttemptId, line: str) -> str:
    return client.post(f"/api/attempt/{attempt_id}/command", data={"line": line}).text


# --- the page --------------------------------------------------------------


def test_a_scenario_gets_a_console_instead_of_an_editor(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)

    body = client.get(f"/attempt/{attempt_id}").text

    assert 'id="console-log"' in body
    assert f"/api/attempt/{attempt_id}/command" in body
    assert f"/api/attempt/{attempt_id}/submit-scenario" in body
    # No editor on this page, and no editor machinery loaded for it either.
    assert "codemirror.min.js" not in body


def test_the_console_names_the_commands_this_exercise_allows(
    client: TestClient, wiring: Wiring
) -> None:
    """From `AttemptPolicy.allowed_commands`, which is the exercise's own list.

    A page that printed a fixed set would be telling the solver about a policy
    other than the one they are being held to -- and the allowlist is per
    exercise, which is the whole reason it is on the spec.
    """
    attempt_id = a_scenario_attempt(wiring)

    body = client.get(f"/attempt/{attempt_id}").text

    assert "<code>git</code>" in body
    assert "<code>cat</code>" in body


def test_the_console_shows_the_budget(client: TestClient, wiring: Wiring) -> None:
    attempt_id = a_scenario_attempt(wiring)

    body = client.get(f"/attempt/{attempt_id}").text

    assert "0 of 25 commands used" in body


# --- running a command ----------------------------------------------------


def test_a_command_runs_in_the_workspace_and_comes_back_as_an_entry(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)

    fragment = run(client, attempt_id, "git status")

    assert "<li" in fragment
    assert "git status" in fragment
    assert wiring.provisioner.workspace_for(attempt_id).commands == [("git", "status")]


def test_a_command_response_is_a_fragment_and_not_a_page(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)

    fragment = run(client, attempt_id, "git status")

    assert "<!DOCTYPE html>" not in fragment
    assert "swe-practice" not in fragment


def test_a_command_response_also_re_renders_the_budget_out_of_band(
    client: TestClient, wiring: Wiring
) -> None:
    """PLAN.md §8.4's contract: one response, the appended output *and* what moved.

    `hx-swap-oob` is what makes that one request rather than two, and it has to be
    on a top-level element of the response for htmx to lift it out — which is why
    the wrapper template exists at all.
    """
    attempt_id = a_scenario_attempt(wiring)

    fragment = run(client, attempt_id, "git status")

    assert 'id="console-status"' in fragment
    assert 'hx-swap-oob="true"' in fragment
    assert "1 of 25 commands used" in fragment


def test_the_page_renders_nothing_out_of_band(
    client: TestClient, wiring: Wiring
) -> None:
    """The flag is per response, not per template.

    A status that carried `hx-swap-oob` on the page as well would make the whole
    workbench an out-of-band swap the first time something targeted it.
    """
    attempt_id = a_scenario_attempt(wiring)

    body = client.get(f"/attempt/{attempt_id}").text

    assert 'id="console-status"' in body
    assert "hx-swap-oob" not in body


def test_a_failing_command_is_reported_rather_than_refused(
    client: TestClient, wiring: Wiring
) -> None:
    """`git revert` hitting a conflict is often the instructive moment.

    So a non-zero exit is a 200 with the output in it, and the only thing that
    changes is the entry's class -- which is read from the exit code and not from
    anything having been written to stderr.
    """
    attempt_id = a_scenario_attempt(wiring)
    wiring.provisioner.workspace_for(attempt_id).result = CommandResult(
        exit_code=1, stdout="CONFLICT (content): Merge conflict in parser.py"
    )

    fragment = run(client, attempt_id, "git revert HEAD")

    assert 'class="entry bad"' in fragment
    assert "Merge conflict in parser.py" in fragment
    assert "exit 1" in fragment


def test_ordinary_progress_on_stderr_is_not_styled_as_failure(
    client: TestClient, wiring: Wiring
) -> None:
    """git writes "Switched to branch 'main'" to stderr. Colouring that as a
    failure would teach something false about what the command did.
    """
    attempt_id = a_scenario_attempt(wiring)
    wiring.provisioner.workspace_for(attempt_id).result = CommandResult(
        exit_code=0, stderr="Switched to branch 'main'"
    )

    fragment = run(client, attempt_id, "git checkout main")

    assert 'class="entry ok"' in fragment
    # Escaped, because it is captured output from a process the solver chose to
    # run -- which is the path `app.py` says autoescaping is load-bearing for.
    assert "Switched to branch &#39;main&#39;" in fragment
    assert "exit 0" not in fragment


def test_truncated_output_says_so(client: TestClient, wiring: Wiring) -> None:
    """The sandbox caps output, and a transcript that quietly stopped mid-file
    would look like a command that printed less than it did.
    """
    attempt_id = a_scenario_attempt(wiring)
    wiring.provisioner.workspace_for(attempt_id).result = CommandResult(
        exit_code=0, stdout="a line\n", truncated=True
    )

    fragment = run(client, attempt_id, "git log")

    assert "truncated" in fragment


def test_the_transcript_is_rebuilt_from_the_event_log_on_reload(
    client: TestClient, wiring: Wiring
) -> None:
    """The browser holds no history of its own.

    Which is what makes a reload, a second tab and an attempt resumed from a
    terminal yesterday all show the same console: `Attempt.commands` is the
    record, and the page is a view of it.
    """
    attempt_id = a_scenario_attempt(wiring)
    run(client, attempt_id, "git status")
    run(client, attempt_id, "git log --oneline")

    body = client.get(f"/attempt/{attempt_id}").text

    assert "git status" in body
    assert "git log --oneline" in body
    assert "2 of 25 commands used" in body


def test_a_command_run_from_the_cli_shows_up_in_the_console(
    client: TestClient, wiring: Wiring
) -> None:
    """The Phase 6 claim, cashed in: one attempt, one log, two driving adapters.

    This drives the use case directly rather than through HTTP, which is exactly
    what `practice resume <id> --commands` does from another process.
    """
    attempt_id = a_scenario_attempt(wiring)
    wiring.services.run_scenario_command(attempt_id, "git reflog")

    body = client.get(f"/attempt/{attempt_id}").text

    assert "git reflog" in body


# --- refusals --------------------------------------------------------------


def test_a_line_with_a_shell_metacharacter_is_refused_in_the_transcript(
    client: TestClient, wiring: Wiring
) -> None:
    """The rejection teaches, so it is rendered where the teaching lands.

    §8.1's argument for rejecting `echo x > f` loudly is that doing nothing
    quietly leaves someone staring at a file that did not change. A refusal
    swapped into the transcript, under the line it is about, is that argument in
    the browser.
    """
    attempt_id = a_scenario_attempt(wiring)

    fragment = run(client, attempt_id, "git log > out.txt")

    assert 'class="entry refused"' in fragment
    assert "git log &gt; out.txt" in fragment
    assert "write" in fragment
    assert wiring.provisioner.workspace_for(attempt_id).commands == []


def test_a_program_the_exercise_does_not_allow_is_refused(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)

    fragment = run(client, attempt_id, "curl https://example.com")

    assert 'class="entry refused"' in fragment
    assert "not allowed" in fragment


def test_an_empty_line_is_refused_with_the_line_it_came_from(
    client: TestClient, wiring: Wiring
) -> None:
    """`parse_command_line` raises sentence fragments -- "is not a command" --
    because its other caller prefixes them with a file and a line number. Here the
    prefix is the echoed line, which is what makes the fragment read.
    """
    attempt_id = a_scenario_attempt(wiring)

    fragment = run(client, attempt_id, "   ")

    assert 'class="entry refused"' in fragment
    assert "not a command" in fragment


def test_a_refusal_does_not_re_render_the_budget(
    client: TestClient, wiring: Wiring
) -> None:
    """A refused command did not run, so nothing it could have spent was spent."""
    attempt_id = a_scenario_attempt(wiring)

    fragment = run(client, attempt_id, "git log | head")

    assert "hx-swap-oob" not in fragment


def test_the_budget_refusal_names_the_limit(client: TestClient, wiring: Wiring) -> None:
    """At zero the browser is not asked to disable anything: the limit is the
    aggregate's, and what the solver gets is the refusal that states it.
    """
    attempt_id = a_scenario_attempt(wiring)
    for _ in range(25):
        run(client, attempt_id, "git status")

    fragment = run(client, attempt_id, "git status")

    assert 'class="entry refused"' in fragment
    assert "budget exhausted" in fragment
    assert "25" in fragment


def test_a_command_against_a_kata_says_katas_have_no_console(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = wiring.services.start_attempt(KATA).attempt.id

    fragment = run(client, attempt_id, "git status")

    assert "no command console" in fragment


def test_a_command_against_an_unknown_attempt_is_still_a_fragment(
    client: TestClient,
) -> None:
    """Not a 404 page: the console is what is on screen, and a page swapped into
    the transcript would replace the thing the reader is looking at with a copy of
    the whole app.
    """
    response = client.post(
        "/api/attempt/00000000-0000-4000-8000-000000000000/command",
        data={"line": "git status"},
    )

    assert response.status_code == 200
    assert "no attempt with id" in response.text
    assert "<!DOCTYPE html>" not in response.text


def test_a_malformed_attempt_id_is_refused_the_same_way(client: TestClient) -> None:
    response = client.post("/api/attempt/oops/command", data={"line": "git status"})

    assert response.status_code == 200
    assert 'class="entry refused"' in response.text


# --- submitting -----------------------------------------------------------


def test_submitting_a_scenario_grades_the_repository_and_returns_the_verdict(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)

    response = client.post(f"/api/attempt/{attempt_id}/submit-scenario")

    assert response.status_code == 200
    assert 'class="outcome' in response.text
    assert wiring.grader.calls


def test_submitting_sends_no_body_at_all(client: TestClient, wiring: Wiring) -> None:
    """The thing being graded is already on disk, and the log already holds every
    command that put it there -- which is `SubmitScenario`'s own argument for
    carrying nothing.
    """
    attempt_id = a_scenario_attempt(wiring)

    response = client.post(f"/api/attempt/{attempt_id}/submit-scenario", content=b"")

    assert response.status_code == 200


def test_a_second_submission_is_refused_into_the_verdict_slot(
    client: TestClient, wiring: Wiring
) -> None:
    """The double-clicked button. The aggregate refuses, and the refusal goes
    where the person who clicked twice is looking.
    """
    attempt_id = a_scenario_attempt(wiring)
    client.post(f"/api/attempt/{attempt_id}/submit-scenario")

    response = client.post(f"/api/attempt/{attempt_id}/submit-scenario")

    assert response.status_code == 200
    assert "is completed" in response.text


def test_a_command_after_submission_is_refused(
    client: TestClient, wiring: Wiring
) -> None:
    """A stale tab. The use case refuses before `attach` is reached, which is the
    finding `RunScenarioCommand` records: otherwise a graded attempt is told its
    workspace is gone and to start again.
    """
    attempt_id = a_scenario_attempt(wiring)
    client.post(f"/api/attempt/{attempt_id}/submit-scenario")

    fragment = run(client, attempt_id, "git status")

    assert "is completed" in fragment


def test_a_finished_scenario_shows_its_verdict_instead_of_the_console(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)
    client.post(f"/api/attempt/{attempt_id}/submit-scenario")

    body = client.get(f"/attempt/{attempt_id}").text

    assert 'id="console-log"' not in body
    assert "Verdict" in body
