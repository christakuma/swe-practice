"""`InspectRepository`: what the repo state panel is handed, and when it refuses.

Pure unit tests. No git, no directory, no subprocess — which is the whole return on
`RepoQuery` being a port and on the inspection reading through it rather than
through a second git-parsing path written for display.

The grouping is what these are mostly about. `refs()` answers with one flat map of
full ref names, correctly, because `branch_exists {name: main}` and
`tag_exists {name: main}` have to be able to disagree; a panel wants the three
kinds apart. That split is the one piece of logic in this module and the one place
it can be wrong.
"""

from __future__ import annotations

import pytest

from practice.application.dto import short_ref
from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    WorkspaceGoneError,
)
from practice.domain.ids import AttemptId, ExerciseId
from tests.unit.application.helpers import (
    World,
    a_start_attempt,
    a_submit_scenario,
    an_environment,
    an_inspect_repository,
)

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")


def a_world_with_a_scenario_attempt() -> tuple[World, AttemptId]:
    world = an_environment()
    started = a_start_attempt(world)(SCENARIO)
    return world, started.attempt.id


def a_three_commit_repo(world: World) -> None:
    """The flagship fixture's shape: skeleton, parser, and the bad refactor."""
    first, _, third = world.repo.chain("skeleton", "working parser", "bad refactor")
    world.repo.branch("main", third)
    world.repo.remote("main", third)
    world.repo.tag("v1", first)
    world.repo.head("refs/heads/main")


# --- what it reports -------------------------------------------------------


def test_it_reports_the_branch_head_is_on() -> None:
    world, attempt_id = a_world_with_a_scenario_attempt()
    a_three_commit_repo(world)

    view = an_inspect_repository(world)(attempt_id)

    assert view is not None
    assert view.head_ref == "refs/heads/main"
    assert view.head_branch == "main"
    assert not view.is_detached


def test_a_detached_head_is_reported_as_detached() -> None:
    """The one fact about a repository this panel exists to make unmissable.

    `rev_parse("HEAD")` answers with a hash whether HEAD is attached or not, so
    this can only come from `head_ref` -- which is the finding that put that method
    on the port in Phase 5.
    """
    world, attempt_id = a_world_with_a_scenario_attempt()
    first, _, third = world.repo.chain("skeleton", "parser", "refactor")
    world.repo.branch("main", third)
    world.repo.detach(first)

    view = an_inspect_repository(world)(attempt_id)

    assert view is not None
    assert view.is_detached
    assert view.head_ref is None
    assert view.head_branch is None
    # Still a commit, and naming it is the point: "detached" alone is a diagnosis
    # with the evidence withheld.
    assert view.head_sha == first


def test_the_three_kinds_of_ref_are_reported_apart() -> None:
    world, attempt_id = a_world_with_a_scenario_attempt()
    a_three_commit_repo(world)

    view = an_inspect_repository(world)(attempt_id)

    assert view is not None
    assert list(view.branches) == ["refs/heads/main"]
    assert list(view.remote_branches) == ["refs/remotes/origin/main"]
    assert list(view.tags) == ["refs/tags/v1"]


def test_a_branch_and_a_tag_of_the_same_name_do_not_collide() -> None:
    """Which is why the port answers with full names and this keeps them.

    A repository may legally hold `refs/heads/release` and `refs/tags/release`, and
    a panel keyed on short names would show one of them twice or neither.
    """
    world, attempt_id = a_world_with_a_scenario_attempt()
    (only,) = world.repo.chain("one")
    world.repo.branch("release", only).tag("release", only)

    view = an_inspect_repository(world)(attempt_id)

    assert view is not None
    assert list(view.branches) == ["refs/heads/release"]
    assert list(view.tags) == ["refs/tags/release"]


def test_refs_come_back_in_a_stable_order() -> None:
    """A panel whose branches reshuffle between two commands is a panel nobody can
    read a change out of, which is the only thing this panel is for.
    """
    world, attempt_id = a_world_with_a_scenario_attempt()
    (only,) = world.repo.chain("one")
    for name in ("zulu", "alpha", "mike"):
        world.repo.branch(name, only)

    view = an_inspect_repository(world)(attempt_id)

    assert view is not None
    assert list(view.branches) == [
        "refs/heads/alpha",
        "refs/heads/mike",
        "refs/heads/zulu",
    ]


def test_it_reports_the_worktree_status() -> None:
    world, attempt_id = a_world_with_a_scenario_attempt()
    a_three_commit_repo(world)
    world.repo.status(staged=["parser.py"], untracked=["scratch.txt"])

    view = an_inspect_repository(world)(attempt_id)

    assert view is not None
    assert view.status.staged == frozenset({"parser.py"})
    assert view.status.untracked == frozenset({"scratch.txt"})
    assert not view.status.is_clean


def test_it_reports_stash_messages_rather_than_a_count() -> None:
    """A stash's message is the only clue to what is in it, and "1 stash" is the
    version of this panel that sends someone back to the terminal.
    """
    world, attempt_id = a_world_with_a_scenario_attempt()
    a_three_commit_repo(world)
    world.repo.stash("WIP on main: 1a2b3c4 the fix I forgot about")

    view = an_inspect_repository(world)(attempt_id)

    assert view is not None
    assert view.stashes == ("WIP on main: 1a2b3c4 the fix I forgot about",)


def test_a_branch_with_no_commit_yet_is_reported_as_unborn() -> None:
    """`git init` and nothing else, or a first commit a solver just reset away.

    A real state, and one the panel has to say out loud: every field being empty
    otherwise reads as a panel that failed to load.
    """
    world, attempt_id = a_world_with_a_scenario_attempt()
    world.repo.head("refs/heads/main")

    view = an_inspect_repository(world)(attempt_id)

    assert view is not None
    assert view.is_unborn
    assert view.head_sha is None
    assert not view.is_detached


def test_a_branch_named_with_a_slash_keeps_its_whole_name() -> None:
    """`feature/parser` shortens to `feature/parser`, not to `parser`.

    Prefix-stripping and not a split on the last slash: two branches under one
    name is a panel that is actively lying about what is there.
    """
    world, attempt_id = a_world_with_a_scenario_attempt()
    (only,) = world.repo.chain("one")
    world.repo.branch("feature/parser", only).head("refs/heads/feature/parser")

    view = an_inspect_repository(world)(attempt_id)

    assert view is not None
    assert view.head_branch == "feature/parser"


# --- what it refuses -------------------------------------------------------


def test_a_finished_attempt_has_no_repository_and_that_is_not_an_error() -> None:
    """Submission disposes of the workspace, so a tab left open across one asks
    for a panel there is nothing to draw. `None`, like `Workbench.workspace`.
    """
    world, attempt_id = a_world_with_a_scenario_attempt()
    a_submit_scenario(world)(attempt_id)

    assert an_inspect_repository(world)(attempt_id) is None


def test_an_unknown_attempt_is_refused() -> None:
    world = an_environment()

    with pytest.raises(AttemptNotFoundError, match="no attempt with id"):
        an_inspect_repository(world)(
            AttemptId.parse("00000000-0000-4000-8000-000000000000")
        )


def test_an_exercise_that_left_the_library_is_refused() -> None:
    world, attempt_id = a_world_with_a_scenario_attempt()
    world.content.forget(SCENARIO)

    with pytest.raises(ExerciseNotFoundError, match="no longer in the library"):
        an_inspect_repository(world)(attempt_id)


def test_a_kata_has_no_repository_to_inspect() -> None:
    """Its workspace is a directory with a stub in it. Every field would come back
    empty, and the panel would read as a repository in a strange state rather than
    as a question that does not apply.
    """
    world = an_environment()
    started = a_start_attempt(world)(KATA)

    with pytest.raises(ExerciseNotFoundError, match="no repository to inspect"):
        an_inspect_repository(world)(started.attempt.id)


def test_an_active_attempt_whose_workspace_is_gone_is_refused() -> None:
    """Distinct from the finished case above, and the distinction is the whole
    reason this is not simply `None` whenever `attach` misses: this attempt can
    still only be abandoned, and saying so is the only honest panel.
    """
    world, attempt_id = a_world_with_a_scenario_attempt()
    world.provisioner.collect(attempt_id)

    with pytest.raises(WorkspaceGoneError, match="abandon it"):
        an_inspect_repository(world)(attempt_id)


def test_inspecting_records_nothing_on_the_attempt() -> None:
    """Looking at the panel is not something the solver did in the exercise.

    The §6.3 process assertions read the event log to decide whether someone
    reached for the reflog; an entry per redraw would make every advisory check
    learn to ignore one kind of entry.
    """
    world, attempt_id = a_world_with_a_scenario_attempt()
    a_three_commit_repo(world)
    before = world.attempts.get(attempt_id)
    assert before is not None
    count = len(before.events)

    an_inspect_repository(world)(attempt_id)
    an_inspect_repository(world)(attempt_id)

    after = world.attempts.get(attempt_id)
    assert after is not None
    assert len(after.events) == count


def test_a_ref_outside_the_three_namespaces_is_shown_whole() -> None:
    """`refs/stash` and `refs/notes/commits` are real refs with no short form.

    Stripping only the three prefixes a reader knows, and returning anything else
    untouched, is the behaviour that cannot mislead: an unfamiliar ref shown in
    full is a ref someone can go and look up.
    """
    assert short_ref("refs/stash") == "refs/stash"
    assert short_ref("refs/heads/main") == "main"
    assert short_ref("refs/remotes/origin/main") == "origin/main"
    assert short_ref("refs/tags/v1") == "v1"
