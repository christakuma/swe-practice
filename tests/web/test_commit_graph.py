"""The SVG renderer, and the graph on the page.

Two halves, deliberately in one file. `render_graph` is a pure function over a
laid-out graph, so most of these build a `CommitGraph` by hand and assert on the
markup; the last few drive the real page, because what the renderer produces is
worth nothing if the panel does not include it.

**The assertions are about the parts a reader of the SVG cannot check by eye.**
Escaping, because a commit subject is text the solver typed into a repository.
Scaling, because the drawing sits in a responsive column. And the `<title>`, which
is what makes truncation honest rather than lossy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.application.graph import lay_out
from practice.domain.ids import ExerciseId, Sha
from practice.domain.ports import CommitInfo
from practice.interface.web.commit_graph import VIEWPORT_WIDTH, render_graph

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from practice.domain.ids import AttemptId
    from tests.web.conftest import Wiring

SCENARIO = ExerciseId("git/revert-a-pushed-commit")


def sha(marker: str) -> Sha:
    """A valid hash per marker; see `tests/unit/application/test_graph.py`."""
    return Sha(marker.encode("utf-8").hex().ljust(40, "0")[:40])


def commit(marker: str, subject: str, *parents: str) -> CommitInfo:
    return CommitInfo(
        sha=sha(marker),
        tree=sha(f"t{marker}"),
        subject=subject,
        parents=tuple(sha(parent) for parent in parents),
    )


def a_scenario_attempt(wiring: Wiring) -> AttemptId:
    return wiring.services.start_attempt(SCENARIO).attempt.id


# --- the renderer ----------------------------------------------------------


def test_an_empty_graph_renders_a_note_rather_than_an_empty_drawing() -> None:
    """A repository with no commits on any ref is a reachable state — a fixture
    whose history the solver has just thrown away — and a zero-height `svg` would
    read as a panel that failed rather than as a repository with nothing in it.
    """
    markup = str(render_graph(lay_out([])))

    assert "<svg" not in markup
    assert "nothing to draw" in markup


def test_each_commit_gets_a_node_and_a_row_of_text() -> None:
    graph = lay_out([commit("c2", "Add parser", "c1"), commit("c1", "Add skeleton")])

    markup = str(render_graph(graph))

    assert markup.count('class="node commit"') == 2
    assert markup.count('class="row"') == 2
    assert "Add parser" in markup
    assert "Add skeleton" in markup


def test_a_linear_history_draws_one_straight_line_per_link() -> None:
    graph = lay_out(
        [
            commit("c3", "three", "c2"),
            commit("c2", "two", "c1"),
            commit("c1", "one"),
        ]
    )

    markup = str(render_graph(graph))

    assert markup.count('class="lane"') == 2
    # `L` for a straight segment, no bezier anywhere in a history with no branches.
    assert " C" not in markup


def test_a_link_that_changes_lane_is_drawn_as_a_curve() -> None:
    """A diagonal straight across two rows is what makes a three-way merge
    unreadable, so the renderer bends instead.
    """
    graph = lay_out(
        [
            commit("mer", "merge", "c2", "fea"),
            commit("c2", "mainline", "c1"),
            commit("fea", "feature", "c1"),
            commit("c1", "base"),
        ]
    )

    markup = str(render_graph(graph))

    assert " C" in markup


def test_a_merge_is_drawn_differently_from_an_ordinary_commit() -> None:
    """The other thing that identifies a merge -- a second line arriving -- is
    exactly what a reader is scanning for and has not found yet.
    """
    graph = lay_out([commit("mer", "merge", "c2", "fea")])

    markup = str(render_graph(graph))

    assert 'class="node merge"' in markup
    assert 'class="node commit"' not in markup


def test_refs_are_drawn_on_the_commit_they_point_at() -> None:
    graph = lay_out(
        [commit("c2", "Add parser", "c1"), commit("c1", "Add skeleton")],
        refs={"refs/heads/main": sha("c2"), "refs/remotes/origin/main": sha("c1")},
    )

    markup = str(render_graph(graph))

    assert ">main<" in markup or "main" in markup
    assert "origin/main" in markup


def test_a_ref_is_shortened_and_never_split_on_its_last_slash() -> None:
    """`feature/parser` is one branch, and showing it as `parser` would put two
    different branches on the page under one name.
    """
    graph = lay_out(
        [commit("c1", "only")], refs={"refs/heads/feature/parser": sha("c1")}
    )

    markup = str(render_graph(graph))

    assert "feature/parser" in markup


def test_a_long_subject_is_truncated_with_the_whole_of_it_in_a_title() -> None:
    """Which is the honest way to shorten something: one hover away, not gone.

    It is also what a screen reader is given for the row, so the truncation does
    not cost the drawing its accessible text.
    """
    subject = "Rename parse_line to parse across every module in the repository"
    graph = lay_out([commit("c1", subject)])

    markup = str(render_graph(graph))

    assert f"<title>{subject}</title>" in markup
    assert "…" in markup


def test_a_subject_is_escaped_rather_than_interpolated() -> None:
    """A commit subject is text the solver typed into a repository they control,
    so this is the normal path and not the exotic one.
    """
    graph = lay_out([commit("c1", "<script>alert(1)</script>")])

    markup = str(render_graph(graph))

    assert "<script>" not in markup
    assert "&lt;script&gt;" in markup


def test_a_ref_name_is_escaped_too() -> None:
    graph = lay_out([commit("c1", "only")], refs={"refs/heads/<odd>": sha("c1")})

    markup = str(render_graph(graph))

    assert "&lt;odd&gt;" in markup


def test_the_drawing_scales_to_its_column_rather_than_clipping() -> None:
    """A fixed `viewBox`, `width="100%"`, and no height attribute, so the browser
    derives the height from the aspect ratio. A panel in a responsive grid gets a
    smaller drawing rather than a cut-off one.
    """
    graph = lay_out([commit("c1", "only")])

    markup = str(render_graph(graph))

    assert f'viewBox="0 0 {VIEWPORT_WIDTH} ' in markup
    assert 'width="100%"' in markup
    assert "height=" not in markup
    assert 'preserveAspectRatio="xMinYMin meet"' in markup


def test_the_drawing_is_labelled_for_a_screen_reader() -> None:
    graph = lay_out([commit("c2", "two", "c1"), commit("c1", "one")])

    markup = str(render_graph(graph))

    assert 'role="img"' in markup
    assert 'aria-label="Commit graph, 2 commits"' in markup


# --- on the page -----------------------------------------------------------


def test_the_graph_is_in_the_repo_state_panel(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)
    first, _, third = wiring.repo.chain("skeleton", "parser", "bad refactor")
    wiring.repo.branch("main", third).head("refs/heads/main")

    body = client.get(f"/attempt/{attempt_id}").text

    assert 'class="commit-graph"' in body
    assert "bad refactor" in body
    assert first.value[:7] in body


def test_the_graph_shows_commits_no_longer_reachable_from_head(
    client: TestClient, wiring: Wiring
) -> None:
    """The whole reason the history is merged across every ref rather than taken
    from HEAD alone.

    After `reset --hard`, the commit still on `origin/main` is unreachable from
    HEAD. A graph that stopped showing it would hide exactly what the solver did,
    which is the lesson the flagship scenario is built around.
    """
    attempt_id = a_scenario_attempt(wiring)
    _, second, third = wiring.repo.chain("skeleton", "parser", "bad refactor")
    wiring.repo.branch("main", second).remote("main", third).head("refs/heads/main")

    body = client.get(f"/attempt/{attempt_id}").text

    assert "bad refactor" in body
    assert "origin/main" in body


def test_the_graph_is_redrawn_by_every_command(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)
    _, second, third = wiring.repo.chain("skeleton", "parser", "bad refactor")
    wiring.repo.branch("main", third).head("refs/heads/main")
    assert "bad refactor" in client.get(f"/attempt/{attempt_id}").text

    wiring.repo.moved("refs/heads/main", second)
    fragment = client.post(
        f"/api/attempt/{attempt_id}/command", data={"line": "git reset --hard HEAD~1"}
    ).text

    assert 'class="commit-graph"' in fragment
    # `main` has moved down a row, which is the change the drawing exists to show.
    assert second.value[:7] in fragment


def test_a_repository_with_no_commits_draws_the_note_on_the_page(
    client: TestClient, wiring: Wiring
) -> None:
    attempt_id = a_scenario_attempt(wiring)

    body = client.get(f"/attempt/{attempt_id}").text

    assert "nothing to draw" in body
