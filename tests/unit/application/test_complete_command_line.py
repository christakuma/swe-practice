"""`CompleteCommandLine`: the words one attempt's repository offers.

The rules are `test_completion.py`'s. What is here is where the words come
from: refs shortened the way people type them, stashes as `stash@{n}`, files
from the working tree, and programs from the exercise's allowlist. Plus the
refusals, which mirror `InspectRepository`'s because the two read the same
repository the same way.
"""

from __future__ import annotations

import pytest

from practice.application.errors import (
    AttemptNotFoundError,
    ExerciseNotFoundError,
    WorkspaceGoneError,
)
from practice.domain.ids import AttemptId, ExerciseId
from tests.unit.application.helpers import (
    World,
    a_complete_command_line,
    a_start_attempt,
    a_submit_scenario,
    an_environment,
)

KATA = ExerciseId("katas/two-sum")
SCENARIO = ExerciseId("git/revert-a-pushed-commit")


def a_world_with_a_repo() -> tuple[World, AttemptId]:
    world = an_environment()
    attempt_id = a_start_attempt(world)(SCENARIO).attempt.id
    first, second = world.repo.chain("skeleton", "parser")
    world.repo.branch("main", second)
    world.repo.branch("feature/webhooks", second)
    world.repo.remote("main", first)
    world.repo.tag("v1", first)
    world.repo.head("refs/heads/main")
    world.repo.stash("WIP on main", "WIP on main")
    world.repo.working_file("parser.py", "def parse(): ...\n")
    world.repo.working_file("tools/build.sh", "make\n")
    return world, attempt_id


def matches(world: World, attempt_id: AttemptId, line: str) -> tuple[str, ...]:
    return a_complete_command_line(world)(attempt_id, line).matches


def test_branches_complete_by_their_short_names() -> None:
    world, attempt_id = a_world_with_a_repo()

    assert matches(world, attempt_id, "git checkout feat") == ("feature/webhooks",)


def test_a_remote_branch_keeps_its_remote() -> None:
    world, attempt_id = a_world_with_a_repo()

    assert matches(world, attempt_id, "git log orig") == ("origin/main",)


def test_tags_and_symbolic_names_are_revisions_too() -> None:
    world, attempt_id = a_world_with_a_repo()

    assert matches(world, attempt_id, "git show v") == ("v1",)
    assert matches(world, attempt_id, "git reset --hard OR") == ("ORIG_HEAD",)


def test_each_stash_entry_is_offered_by_its_index() -> None:
    world, attempt_id = a_world_with_a_repo()

    assert matches(world, attempt_id, "git stash show st") == (
        "stash@{0}",
        "stash@{1}",
    )


def test_files_come_from_the_working_tree() -> None:
    world, attempt_id = a_world_with_a_repo()

    done = a_complete_command_line(world)(attempt_id, "cat too")

    assert done.line == "cat tools/"


def test_programs_come_from_the_exercises_allowlist() -> None:
    world, attempt_id = a_world_with_a_repo()

    assert "git" in matches(world, attempt_id, "")


def test_a_finished_attempt_completes_nothing() -> None:
    world, attempt_id = a_world_with_a_repo()
    a_submit_scenario(world)(attempt_id)

    done = a_complete_command_line(world)(attempt_id, "git che")

    assert (done.line, done.matches) == ("git che", ())


def test_an_unknown_attempt_is_refused() -> None:
    world = an_environment()

    with pytest.raises(AttemptNotFoundError):
        a_complete_command_line(world)(
            AttemptId.parse("00000000-0000-4000-8000-000000000000"), "git"
        )


def test_an_exercise_that_left_the_library_is_refused() -> None:
    world, attempt_id = a_world_with_a_repo()
    world.content.forget(SCENARIO)

    with pytest.raises(ExerciseNotFoundError, match="no longer in the library"):
        a_complete_command_line(world)(attempt_id, "git")


def test_a_kata_has_no_console_to_complete() -> None:
    world = an_environment()
    started = a_start_attempt(world)(KATA)

    with pytest.raises(ExerciseNotFoundError, match="has no console"):
        a_complete_command_line(world)(started.attempt.id, "git")


def test_an_active_attempt_whose_workspace_is_gone_is_refused() -> None:
    world, attempt_id = a_world_with_a_repo()
    world.provisioner.collect(attempt_id)

    with pytest.raises(WorkspaceGoneError):
        a_complete_command_line(world)(attempt_id, "git")


def test_a_ref_outside_the_three_namespaces_is_not_offered() -> None:
    """`refs/stash` is typed as `stash@{0}`, which is offered already."""
    world, attempt_id = a_world_with_a_repo()
    first = world.repo.chain("stashed")[0]
    world.repo.ref("refs/stash", first)

    assert matches(world, attempt_id, "git show refs") == ()


def test_remotes_are_read_off_the_remote_tracking_refs() -> None:
    world, attempt_id = a_world_with_a_repo()

    assert matches(world, attempt_id, "git fetch o") == ("origin",)
