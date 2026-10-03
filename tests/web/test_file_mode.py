"""`POST /api/attempt/{id}/editor` — the panel that hands over the file.

Fragment assertions, like every other route test here: what comes back is meant
to be swapped into `#file-mode` and nothing else. The editor behind these is the
fake — whether a `code.CMD` can be started is
`tests/integration/sandbox/test_editor.py`'s question, and a web suite that
opened VS Code is a web suite nobody runs twice.

The three things worth holding this route to are the three the fragment is for:
the path is always on it, the handoff reaches the file, and a launch that failed
says so *and still shows the path*.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.ids import ExerciseId
from tests.web.conftest import a_wiring, client_for

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")

TYPED = "def two_sum(numbers, target):\n    return (0, 1)\n"


def editor_url(attempt_id: object) -> str:
    return f"/api/attempt/{attempt_id}/editor"


def test_the_workbench_offers_the_button_for_an_active_kata(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)

    page = client.get(f"/attempt/{started.attempt.id}")

    assert 'id="open-editor"' in page.text
    assert editor_url(started.attempt.id) in page.text


def test_a_git_scenario_is_not_offered_an_editor(
    client: TestClient, wiring: Wiring
) -> None:
    """Its surface is a console over a repository; there is no one file to open,
    which is why the use case refuses one. A page that drew the button anyway
    would be a page with a control that cannot work.
    """
    started = wiring.services.start_attempt(SCENARIO)

    page = client.get(f"/attempt/{started.attempt.id}")

    assert 'id="open-editor"' not in page.text


def test_revealing_returns_the_path_as_a_fragment(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)
    workspace = wiring.provisioner.workspace_for(started.attempt.id)

    response = client.post(editor_url(started.attempt.id), data={"source": TYPED})

    assert response.status_code == 200
    assert str(workspace.resolve("stub.py")) in response.text
    assert "Opened in your editor" in response.text
    # A fragment, not a page: it is swapped into `#file-mode`, and a layout
    # there would nest the whole app inside itself.
    assert "<html" not in response.text


def test_revealing_writes_what_was_on_screen_into_the_file(
    client: TestClient, wiring: Wiring
) -> None:
    """The handoff. Someone who typed in the browser and then switched must not
    lose it, so the page sends the editor's contents and they land in the file.
    """
    started = wiring.services.start_attempt(KATA)

    client.post(editor_url(started.attempt.id), data={"source": TYPED})

    workspace = wiring.provisioner.workspace_for(started.attempt.id)
    assert workspace.read_file("stub.py") == TYPED


def test_revealing_opens_that_file_and_no_other(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)

    client.post(editor_url(started.attempt.id), data={"source": TYPED})

    workspace = wiring.provisioner.workspace_for(started.attempt.id)
    assert wiring.editor.revealed == [workspace.resolve("stub.py")]


def test_an_editor_that_would_not_start_is_reported_with_the_path() -> None:
    """The branch the three-field DTO exists for, through the route.

    `EditorLauncher` returns the problem rather than raising it so that this is
    a panel and not an error page -- and the panel's whole value in this case is
    the path, which the solver now has to open themselves.
    """
    wiring = a_wiring()
    wiring.editor.problem = "'code' is not on this machine's PATH"
    with client_for(wiring) as client:
        started = wiring.services.start_attempt(KATA)
        workspace = wiring.provisioner.workspace_for(started.attempt.id)

        response = client.post(editor_url(started.attempt.id), data={"source": TYPED})

    assert response.status_code == 200
    # Asserted without the apostrophe, because the template escapes it: the
    # sentence comes from an adapter and reaches a page on the normal path, and
    # autoescaping is load-bearing here rather than hygiene (see `app.py`).
    assert "is not on this machine" in response.text
    assert str(workspace.resolve("stub.py")) in response.text


def test_revealing_a_scenario_is_refused_in_the_panel(
    client: TestClient, wiring: Wiring
) -> None:
    """A refusal lands where the button was, because that is where the reader is
    looking -- and the status is 200, because htmx does not swap a 4xx by
    default and a refusal sent as one would vanish.
    """
    started = wiring.services.start_attempt(SCENARIO)

    response = client.post(editor_url(started.attempt.id), data={"source": TYPED})

    assert response.status_code == 200
    assert "no solution file" in response.text


def test_revealing_a_finished_attempt_is_refused(
    client: TestClient, wiring: Wiring
) -> None:
    started = wiring.services.start_attempt(KATA)
    client.post(f"/api/attempt/{started.attempt.id}/submit", data={"source": TYPED})

    response = client.post(editor_url(started.attempt.id), data={"source": TYPED})

    assert response.status_code == 200
    assert "completed" in response.text


def test_a_malformed_attempt_id_is_refused_rather_than_crashing(
    client: TestClient,
) -> None:
    response = client.post(editor_url("oops"), data={"source": TYPED})

    assert response.status_code == 200
    assert "oops" in response.text
