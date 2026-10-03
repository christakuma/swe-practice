"""`lay_out`: lanes, edges, and the shapes that break a naive version of it.

Pure, with no git and no repository — the commits here are built by hand because
the input is a `CommitInfo` sequence and nothing about the layout cares where that
sequence came from.

The cases are chosen for what can go wrong rather than for coverage. A linear
history is one straight column or the whole thing is unreadable; a merge has to
close the lane it merged in, or every later branch drifts a column to the right;
and an edge must end where its parent is actually drawn, which is the defect the
two-pass resolution exists to prevent.
"""

from __future__ import annotations

from practice.application.graph import lay_out, merge_logs
from practice.domain.ids import Sha
from practice.domain.ports import CommitInfo


def sha(marker: str) -> Sha:
    """A valid 40-hex hash per marker, derived from the marker's own bytes.

    So the *test bodies* can say `merge` and `gone` while `Sha` gets the hex it
    rightly insists on. Derived rather than counted, so there is no module-level
    state and no test that depends on which other tests ran first -- and distinct
    markers cannot collide, because the encoding is injective for anything short
    enough to fit.
    """
    return Sha(marker.encode("utf-8").hex().ljust(40, "0")[:40])


def commit(marker: str, *parents: str) -> CommitInfo:
    return CommitInfo(
        sha=sha(marker),
        tree=sha(f"a{marker}"),
        subject=f"commit {marker}",
        parents=tuple(sha(parent) for parent in parents),
    )


def lanes_of(commits: list[CommitInfo]) -> list[int]:
    return [row.lane for row in lay_out(commits).rows]


# --- the ordinary shapes ---------------------------------------------------


def test_an_empty_history_lays_out_to_nothing() -> None:
    graph = lay_out([])

    assert graph.is_empty
    assert graph.lanes == 0
    assert graph.edges == ()


def test_a_linear_history_is_one_straight_column() -> None:
    """The property everything else is judged against: a repository with no
    branching must not spend a lane on anything.
    """
    history = [commit("c3", "c2"), commit("c2", "c1"), commit("c1")]

    graph = lay_out(history)

    assert [row.lane for row in graph.rows] == [0, 0, 0]
    assert graph.lanes == 1
    assert all(edge.is_straight for edge in graph.edges)


def test_every_parent_link_inside_the_window_becomes_an_edge() -> None:
    history = [commit("c3", "c2"), commit("c2", "c1"), commit("c1")]

    graph = lay_out(history)

    assert [(edge.from_row, edge.to_row) for edge in graph.edges] == [(0, 1), (1, 2)]


def test_a_root_commit_has_no_edge_below_it() -> None:
    graph = lay_out([commit("c1")])

    assert graph.edges == ()
    assert graph.lanes == 1


def test_a_diverged_branch_takes_a_second_lane() -> None:
    """Two tips over one base. The second tip cannot share a lane with the first,
    because the first is still waiting to be joined to its own parent.
    """
    history = [commit("b1", "c1"), commit("a1", "c1"), commit("c1")]

    graph = lay_out(history)

    assert [row.lane for row in graph.rows] == [0, 1, 0]
    assert graph.lanes == 2


def test_the_base_of_a_diverged_branch_is_drawn_once_in_the_leftmost_lane() -> None:
    """Both tips reserve a lane for the base, and it is drawn in exactly one.

    Leftmost rather than either, so the mainline stays where a reader left it
    instead of drifting right every time two branches come back together.
    """
    history = [commit("b1", "c1"), commit("a1", "c1"), commit("c1")]

    graph = lay_out(history)

    assert graph.rows[2].lane == 0


def test_both_edges_into_a_shared_parent_end_where_it_is_drawn() -> None:
    """The defect the second pass exists for.

    Resolving an edge from the *reservation* would send one of these to lane 1,
    which is a column the parent is not in -- a line that stops next to the commit
    it was supposed to reach.
    """
    history = [commit("b1", "c1"), commit("a1", "c1"), commit("c1")]

    graph = lay_out(history)

    into_base = [edge for edge in graph.edges if edge.to_row == 2]
    assert len(into_base) == 2
    assert {edge.to_lane for edge in into_base} == {0}
    assert {edge.from_lane for edge in into_base} == {0, 1}


# --- merges ----------------------------------------------------------------


def test_a_merge_keeps_its_first_parent_in_its_own_lane() -> None:
    """Which is what makes the mainline readable through a merge: `git log --graph`
    makes the same choice, and so does every tool for a repository people work in.
    """
    history = [
        commit("m", "c2", "f1"),
        commit("c2", "c1"),
        commit("f1", "c1"),
        commit("c1"),
    ]

    graph = lay_out(history)

    assert graph.rows[0].lane == 0  # the merge
    assert graph.rows[1].lane == 0  # first parent, same lane
    assert graph.rows[2].lane == 1  # second parent, off to the side
    assert graph.rows[0].is_merge


def test_a_merge_produces_an_edge_to_each_parent() -> None:
    history = [
        commit("m", "c2", "f1"),
        commit("c2", "c1"),
        commit("f1", "c1"),
        commit("c1"),
    ]

    graph = lay_out(history)

    from_merge = [edge for edge in graph.edges if edge.from_row == 0]
    assert {edge.to_row for edge in from_merge} == {1, 2}
    # One straight down the mainline, one across to the side lane.
    assert sorted(edge.to_lane for edge in from_merge) == [0, 1]


def test_a_merged_branch_gives_its_lane_back() -> None:
    """Otherwise every later branch starts a column further right, and a history
    with five merges in it is drawn five lanes wide for no reason.
    """
    history = [
        commit("m", "c2", "f1"),
        commit("c2", "c1"),
        commit("f1", "c1"),
        commit("c1"),
        commit("c0"),
    ]

    graph = lay_out(history)

    assert graph.lanes == 2
    # c1 is drawn in lane 0, and the lane f1 was using is closed by the time the
    # root below it is laid out.
    assert graph.rows[3].lane == 0
    assert graph.rows[4].lane == 0


def test_an_octopus_merge_opens_a_lane_for_every_extra_parent() -> None:
    """Rare, legal, and the one shape that proves nothing here assumes two."""
    history = [
        commit("m", "a", "b", "c"),
        commit("a"),
        commit("b"),
        commit("c"),
    ]

    graph = lay_out(history)

    assert [row.lane for row in graph.rows] == [0, 0, 1, 2]
    assert len([edge for edge in graph.edges if edge.from_row == 0]) == 3


# --- windows ---------------------------------------------------------------


def test_a_parent_below_the_window_is_not_an_edge() -> None:
    """A panel shows a slice of history, so a parent off the bottom is normal.

    An edge to a row that does not exist is one a renderer has to invent an end
    for, which is the thing to not make its problem.
    """
    graph = lay_out([commit("c3", "c2")])

    assert graph.edges == ()
    assert graph.rows[0].lane == 0


def test_the_limit_truncates_before_laying_out_rather_than_after() -> None:
    """The only order with no dangling edges: cutting rows afterwards would leave
    edges pointing past the end of the drawing.
    """
    history = [commit("c3", "c2"), commit("c2", "c1"), commit("c1")]

    graph = lay_out(history, limit=2)

    assert len(graph.rows) == 2
    assert [(edge.from_row, edge.to_row) for edge in graph.edges] == [(0, 1)]


def test_a_lane_whose_commit_fell_outside_the_window_is_closed() -> None:
    """So the drawing does not keep a column open for a commit it will never show."""
    history = [commit("b1", "gone"), commit("a1")]

    graph = lay_out(history)

    assert [row.lane for row in graph.rows] == [0, 0]


# --- labels ----------------------------------------------------------------


def test_refs_are_attached_to_the_commits_they_point_at() -> None:
    history = [commit("c2", "c1"), commit("c1")]

    graph = lay_out(history, refs={"refs/heads/main": sha("c2")})

    assert graph.rows[0].refs == ("refs/heads/main",)
    assert graph.rows[1].refs == ()


def test_several_refs_on_one_commit_all_appear() -> None:
    """`main` and `origin/main` on one tip is the published state the flagship
    scenario starts in, so this is the normal case and not an edge one.
    """
    history = [commit("c2", "c1"), commit("c1")]

    graph = lay_out(
        history,
        refs={"refs/heads/main": sha("c2"), "refs/remotes/origin/main": sha("c2")},
    )

    assert set(graph.rows[0].refs) == {"refs/heads/main", "refs/remotes/origin/main"}


def test_the_ref_head_is_on_is_listed_first() -> None:
    """Where you are is the thing being looked for, so it is not sorted into the
    middle of four other names.
    """
    history = [commit("c2", "c1"), commit("c1")]

    graph = lay_out(
        history,
        refs={
            "refs/heads/zulu": sha("c2"),
            "refs/heads/main": sha("c2"),
            "refs/remotes/origin/main": sha("c2"),
        },
        head_ref="refs/heads/zulu",
    )

    assert graph.rows[0].refs[0] == "refs/heads/zulu"


def test_labels_are_in_a_stable_order_when_head_is_not_among_them() -> None:
    history = [commit("c2", "c1"), commit("c1")]

    graph = lay_out(
        history,
        refs={"refs/tags/v2": sha("c2"), "refs/heads/main": sha("c2")},
        head_ref=None,
    )

    assert graph.rows[0].refs == ("refs/heads/main", "refs/tags/v2")


def test_a_ref_pointing_outside_the_window_labels_nothing() -> None:
    graph = lay_out([commit("c1")], refs={"refs/heads/other": sha("c9")})

    assert graph.rows[0].refs == ()


# --- the edge value --------------------------------------------------------


def test_a_straight_edge_knows_it_is_straight() -> None:
    """Which is what lets a renderer draw most lines as a single vertical stroke
    and reserve the curve for the few that actually move.
    """
    history = [commit("m", "c2", "f1"), commit("c2", "c1"), commit("f1"), commit("c1")]

    graph = lay_out(history)

    by_target = {edge.to_row: edge for edge in graph.edges if edge.from_row == 0}
    assert by_target[1].is_straight
    assert not by_target[2].is_straight


# --- merging several logs --------------------------------------------------


def test_merging_nothing_is_nothing() -> None:
    assert merge_logs([]) == ()


def test_one_log_comes_back_in_its_own_order() -> None:
    history = [commit("c3", "c2"), commit("c2", "c1"), commit("c1")]

    assert list(merge_logs([history])) == history


def test_every_commit_comes_before_its_own_parents() -> None:
    """The property `lay_out` depends on: it reserves a lane for each parent as it
    walks down, and a parent emitted above its child would be drawn before anything
    had reserved one for it.
    """
    mainline = [commit("c2", "c1"), commit("c1")]
    published = [commit("c3", "c2"), commit("c2", "c1"), commit("c1")]

    merged = merge_logs([mainline, published])

    positions = {info.sha: index for index, info in enumerate(merged)}
    for info in merged:
        for parent in info.parents:
            if parent in positions:
                assert positions[info.sha] < positions[parent]


def test_a_commit_only_the_second_log_can_reach_is_still_included() -> None:
    """The reason this function exists.

    After `git reset --hard HEAD~1` the commit still on `origin/main` is
    unreachable from HEAD, and a drawing taken from HEAD alone would hide the one
    thing the flagship scenario is about.
    """
    mainline = [commit("c2", "c1"), commit("c1")]
    published = [commit("c3", "c2"), commit("c2", "c1"), commit("c1")]

    merged = merge_logs([mainline, published])

    assert sha("c3") in {info.sha for info in merged}
    assert len(merged) == 3


def test_a_commit_in_two_logs_appears_once() -> None:
    shared = [commit("c2", "c1"), commit("c1")]

    merged = merge_logs([shared, shared])

    assert len(merged) == 2


def test_the_order_is_the_same_whichever_time_it_is_asked_for() -> None:
    """Deterministic, so two redraws of one repository do not reshuffle the
    drawing under someone reading it for what changed.
    """
    logs = [
        [commit("b1", "c1"), commit("c1")],
        [commit("a1", "c1"), commit("c1")],
    ]

    assert merge_logs(logs) == merge_logs(logs)


def test_a_merged_history_lays_out_without_a_dangling_edge() -> None:
    """The two halves together, which is how they are actually used."""
    mainline = [commit("c2", "c1"), commit("c1")]
    published = [commit("c3", "c2"), commit("c2", "c1"), commit("c1")]

    graph = lay_out(merge_logs([mainline, published]))

    rows = len(graph.rows)
    assert all(edge.to_row < rows and edge.from_row < rows for edge in graph.edges)
    assert all(edge.from_row < edge.to_row for edge in graph.edges)


def test_two_merges_sharing_a_side_branch_reserve_one_lane_for_it() -> None:
    """Not a reservation each, which would draw the same branch in two columns.

    Rare in a practice fixture and perfectly legal in a real repository: two
    merges of the same topic branch at different points.
    """
    history = [
        commit("m2", "m1", "fea"),
        commit("m1", "c1", "fea"),
        commit("fea", "c1"),
        commit("c1"),
    ]

    graph = lay_out(history)

    assert graph.lanes == 2
    assert graph.rows[2].lane == 1
    into_feature = [edge for edge in graph.edges if edge.to_row == 2]
    assert {edge.to_lane for edge in into_feature} == {1}


def test_a_parent_outside_the_merged_set_does_not_hold_anything_up() -> None:
    """A log is a window, so the oldest commit in it usually has a parent nobody
    passed in. Waiting for it would mean emitting nothing at all.
    """
    merged = merge_logs([[commit("c2", "c1")]])

    assert [info.sha for info in merged] == [sha("c2")]
