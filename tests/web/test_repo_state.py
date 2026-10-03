"""The repo state panel: what it shows, and that every command redraws it.

`InspectRepository`'s own behaviour — the grouping, the refusals — is covered in
`tests/unit/application/`. What only this layer can show is that the panel reaches
the page at all, and that a command's response carries it out of band, which is the
PLAN.md §8.4 contract and the thing that makes the refs visibly move.

The repository these drive is `wiring.repo`, a `RepoBuilder`. The factory behind
`Services.repo_query` rebuilds from it on every call, so a test arranges the shape
it is about *after* starting the attempt — which is the order these read in, and the
order the real factory allows because it, too, builds one query per call.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.domain.ids import ExerciseId

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from practice.domain.ids import AttemptId, Sha
    from tests.web.conftest import Wiring

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")


def a_scenario_attempt(wiring: Wiring) -> AttemptId:
    return wiring.services.start_attempt(SCENARIO).attempt.id


def a_published_repo(wiring: Wiring) -> tuple[Sha, Sha, Sha]:
    """The flagship fixture's shape: `main` and `origin/main` on a bad refactor."""
    first, second, third = wiring.repo.chain("skeleton", "parser", "bad refactor")
    wiring.repo.branch("main", third)
    wiring.repo.remote("main", third)
    wiring.repo.head("refs/heads/main")
    return first, second, third


# --- on the page -----------------------------------------------------------


def test_the_panel_is_on_the_scenario_workbench(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)
    a_published_repo(wiring)

    body = client.get(f"/attempt/{attempt_id}").text

    assert 'id="repo-state"' in body
    assert "Repository" in body


def test_the_panel_shows_the_branch_head_is_on_and_what_it_points_at(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)
    _, _, third = a_published_repo(wiring)

    body = client.get(f"/attempt/{attempt_id}").text

    assert "<code>main</code>" in body
    assert third.short in body


def test_a_detached_head_is_called_out(client: TestClient, wiring: Wiring) -> None:
    """The state these exercises are mostly about, and the one a terminal hides
    behind a paragraph of advice nobody reads twice.
    """
    attempt_id = a_scenario_attempt(wiring)
    first, _, _ = a_published_repo(wiring)
    wiring.repo.detach(first)

    body = client.get(f"/attempt/{attempt_id}").text

    assert "detached" in body
    # The commit as well as the diagnosis.
    assert first.short in body


def test_remote_branches_are_shown_apart_from_local_ones(
    client: TestClient, wiring: Wiring
) -> None:
    """ "What does `origin/main` point at" is a different question from "what does
    `main` point at" -- it is "have you published this?", which is the flagship
    scenario's `fix-published` check.
    """
    attempt_id = a_scenario_attempt(wiring)
    a_published_repo(wiring)

    body = client.get(f"/attempt/{attempt_id}").text

    assert "<code>origin/main</code>" in body


def test_a_branch_with_a_slash_in_it_keeps_its_whole_name(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)
    (only,) = wiring.repo.chain("one")
    wiring.repo.branch("feature/parser", only).head("refs/heads/feature/parser")

    body = client.get(f"/attempt/{attempt_id}").text

    assert "<code>feature/parser</code>" in body


def test_a_clean_worktree_says_so(client: TestClient, wiring: Wiring) -> None:
    attempt_id = a_scenario_attempt(wiring)
    a_published_repo(wiring)

    body = client.get(f"/attempt/{attempt_id}").text

    assert "clean" in body


def test_the_four_worktree_states_are_reported_apart(
    client: TestClient, wiring: Wiring
) -> None:
    """Four different problems with four different fixes."""
    attempt_id = a_scenario_attempt(wiring)
    a_published_repo(wiring)
    wiring.repo.status(
        staged=["staged.py"],
        unstaged=["modified.py"],
        untracked=["scratch.txt"],
        unmerged=["conflicted.py"],
    )

    body = client.get(f"/attempt/{attempt_id}").text

    assert 'class="staged"' in body
    assert 'class="unstaged"' in body
    assert 'class="untracked"' in body
    assert 'class="unmerged"' in body


def test_untracked_files_alone_are_shown_and_still_called_clean(
    client: TestClient, wiring: Wiring
) -> None:
    """`worktree_clean` ignores untracked files by default (PLAN.md §6.5), so a
    panel that lumped them in would show a repository as dirty that the grader is
    about to call clean -- which is the one disagreement this panel must not have.
    """
    attempt_id = a_scenario_attempt(wiring)
    a_published_repo(wiring)
    wiring.repo.status(untracked=["scratch.txt"])

    body = client.get(f"/attempt/{attempt_id}").text

    assert "scratch.txt" in body
    assert "counts as clean" in body


def test_a_stash_is_shown_with_its_message(client: TestClient, wiring: Wiring) -> None:
    """The thing people forget, which is exactly why it is on the page."""
    attempt_id = a_scenario_attempt(wiring)
    a_published_repo(wiring)
    wiring.repo.stash("WIP on main: the fix I forgot about")

    body = client.get(f"/attempt/{attempt_id}").text

    assert "the fix I forgot about" in body


def test_an_empty_stash_says_empty(client: TestClient, wiring: Wiring) -> None:
    attempt_id = a_scenario_attempt(wiring)
    a_published_repo(wiring)

    body = client.get(f"/attempt/{attempt_id}").text

    assert "empty" in body


def test_a_kata_gets_no_panel(client: TestClient, wiring: Wiring) -> None:
    """`InspectRepository` refuses a kata rather than inventing an empty
    repository for it, so the page must not ask.
    """
    started = wiring.services.start_attempt(KATA)

    body = client.get(f"/attempt/{started.attempt.id}").text

    assert 'id="repo-state"' not in body


def test_a_finished_scenario_says_the_workspace_was_disposed_of(
    client: TestClient, wiring: Wiring
) -> None:
    """Which is the lifecycle (§8.1), not a failure -- so the panel renders and
    says what happened rather than refusing to render at all.
    """
    attempt_id = a_scenario_attempt(wiring)
    a_published_repo(wiring)
    client.post(f"/api/attempt/{attempt_id}/submit-scenario")

    body = client.get(f"/attempt/{attempt_id}").text

    assert "disposed of" in body


# --- redrawn by every command ---------------------------------------------


def test_a_command_response_carries_the_panel_out_of_band(
    client: TestClient, wiring: Wiring
) -> None:
    """One request, the appended output *and* the re-rendered panel. §8.4."""
    attempt_id = a_scenario_attempt(wiring)
    a_published_repo(wiring)

    fragment = client.post(
        f"/api/attempt/{attempt_id}/command", data={"line": "git status"}
    ).text

    assert 'id="repo-state"' in fragment
    assert 'hx-swap-oob="true"' in fragment


def test_the_panel_in_a_command_response_reflects_the_repository_now(
    client: TestClient, wiring: Wiring
) -> None:
    """The point of re-reading rather than patching: the panel is built from a
    fresh query, so a ref the command moved shows up without the page knowing
    which commands move which refs.
    """
    attempt_id = a_scenario_attempt(wiring)
    _, second, third = a_published_repo(wiring)
    assert third.short in client.get(f"/attempt/{attempt_id}").text

    # What `git reset --hard HEAD~1` leaves: `main` back a commit, `origin/main`
    # where it was. The flagship scenario's whole lesson, as two refs.
    wiring.repo.moved("refs/heads/main", second)

    fragment = client.post(
        f"/api/attempt/{attempt_id}/command", data={"line": "git reset --hard HEAD~1"}
    ).text

    assert second.short in fragment
    # And `origin/main` still names the commit that was published.
    assert third.short in fragment


def test_a_refused_command_does_not_redraw_the_panel(
    client: TestClient, wiring: Wiring
) -> None:
    """Nothing ran, so nothing moved, and a redraw would cost a `git` process to
    show the same repository back.
    """
    attempt_id = a_scenario_attempt(wiring)
    a_published_repo(wiring)

    fragment = client.post(
        f"/api/attempt/{attempt_id}/command", data={"line": "git log | head"}
    ).text

    assert 'id="repo-state"' not in fragment
