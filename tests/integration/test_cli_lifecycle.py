"""The lifecycle commands, each on its own: start, attempts, resume, submit, abandon.

Integration tests because every one of them provisions a real workspace and writes
to a real database — which is the point: the claim this phase makes is that an
attempt outlives the process that created it, and a suite that shared one in-memory
store between invocations could not test it.

Each `runner.invoke` is a separate command against the same two paths, exactly as
two shell invocations are. The e2e suite checks the *journey* through all of them;
this one checks each command's own behaviour, especially the refusals, which is
where a lifecycle command earns its keep — `resume` on a graded attempt, `submit`
with the other kind's flag, `gc` on a workspace that is still in use.
"""

from __future__ import annotations

import shutil
import stat
from pathlib import Path

import pytest
from typer.testing import CliRunner

from practice.interface.cli.main import app

TWO_SUM = "katas/two-sum"
REVERT = "git/revert-a-pushed-commit"

SOLVED = """\
def two_sum(numbers, target):
    seen = {}
    for index, value in enumerate(numbers):
        complement = target - value
        if complement in seen:
            return (seen[complement], index)
        seen[value] = index
    raise ValueError("no pair of values adds up to the target")
"""

runner = CliRunner()


@pytest.fixture
def storage(tmp_path: Path) -> tuple[Path, Path]:
    """A disposable workspace root and database, as every invocation gets."""
    return tmp_path / "ws", tmp_path / "practice.db"


def run(storage: tuple[Path, Path], *arguments: str) -> tuple[int, str]:
    """One command, with both paths passed explicitly.

    Passed rather than left to the environment so a failure names them, and so these
    tests do not depend on the autouse database fixture being the thing that saved
    them from writing to a real history.
    """
    workspaces, database = storage
    result = runner.invoke(
        app,
        [
            *arguments,
            "--workspace-root",
            str(workspaces),
            "--database",
            str(database),
        ],
    )
    return result.exit_code, result.output


def start(storage: tuple[Path, Path], exercise: str) -> str:
    """Start an attempt and return its id, as a solver would read it off the screen."""
    code, output = run(storage, "start", exercise, "--no-prompt")
    assert code == 0, output
    for line in output.splitlines():
        if "attempt " in line:
            return line.split("attempt ", 1)[1].strip()
    raise AssertionError(f"no attempt id in:\n{output}")


# --- start -----------------------------------------------------------------


def test_start_leaves_the_attempt_open(storage: tuple[Path, Path]) -> None:
    """The command that makes the other four worth having, and the one that could
    not exist before the attempt table.
    """
    attempt_id = start(storage, REVERT)

    code, output = run(storage, "attempts")

    assert code == 0, output
    assert attempt_id in output
    assert "1 open attempt" in output


def test_start_provisions_the_repository_before_it_returns(
    storage: tuple[Path, Path],
) -> None:
    """So the fixture has run and the repository is waiting. `gc` seeing it is how
    that is observable from outside without reaching into the workspace.
    """
    start(storage, REVERT)

    code, output = run(storage, "gc")

    assert code == 0, output
    assert "1 in use, 0 orphans" in output


def test_start_opens_a_practice_run_by_default(storage: tuple[Path, Path]) -> None:
    """No flag, no change: the hints are counted as they always were and no clock
    is mentioned at all.
    """
    code, output = run(storage, "start", TWO_SUM, "--no-prompt")

    assert code == 0, output
    assert "hints" in output
    assert "limit" not in output
    assert "left" not in output


def test_start_interview_withholds_the_hints_and_states_the_limit(
    storage: tuple[Path, Path],
) -> None:
    """Both clauses on one line. "0 of 0 hints" is true of every interview attempt
    and tells the solver nothing, so it becomes `no hints`.
    """
    code, output = run(storage, "start", TWO_SUM, "--no-prompt", "--interview")

    assert code == 0, output
    assert "no hints" in output
    assert "15 minute limit" in output


def test_start_interview_does_not_print_the_workspace_path(
    storage: tuple[Path, Path],
) -> None:
    """Phase 15's third clause in the CLI. The workspace holds a kata's
    `tests.py`, and naming the directory is the tool offering to show it.
    """
    workspaces, _ = storage

    code, output = run(storage, "start", TWO_SUM, "--no-prompt", "--interview")

    assert code == 0, output
    assert str(workspaces) not in output
    assert "stub.py" not in output


def test_start_interview_still_says_how_to_submit(
    storage: tuple[Path, Path],
) -> None:
    """A withdrawn affordance with no alternative named is a dead end. `--source`
    still works on a file the solver wrote themselves, which is what an interview
    looks like.
    """
    code, output = run(storage, "start", TWO_SUM, "--no-prompt", "--interview")

    assert code == 0, output
    assert "--source FILE" in output
    assert "a file of your own" in output


def test_a_practice_start_still_hands_over_the_path(
    storage: tuple[Path, Path],
) -> None:
    """The regression that keeps own-editor mode working for everybody else."""
    code, output = run(storage, "start", TWO_SUM, "--no-prompt")

    assert code == 0, output
    assert "stub.py" in output


def test_resume_counts_the_interview_clock_down(storage: tuple[Path, Path]) -> None:
    """`start` prints the limit because the attempt has just begun; `resume` is
    where a countdown is the point, and the two read differently on purpose.
    """
    code, output = run(storage, "start", TWO_SUM, "--no-prompt", "--interview")
    assert code == 0, output
    attempt_id = next(
        line.split("attempt ", 1)[1].strip()
        for line in output.splitlines()
        if "attempt " in line
    )

    code, output = run(storage, "resume", attempt_id)

    assert code == 0, output
    assert "15 minutes left" in output


def test_the_mode_belongs_to_the_attempt_not_the_invocation(
    storage: tuple[Path, Path],
) -> None:
    """The reason the mode is stored rather than read from a flag each time: a
    `resume` that passed no `--interview` must not quietly offer the hints back.

    The same claim `test_the_budget_belongs_to_the_attempt_not_the_invocation`
    makes about the command budget, which is where the pattern came from.
    """
    code, output = run(storage, "start", REVERT, "--no-prompt", "--interview")
    assert code == 0, output
    attempt_id = next(
        line.split("attempt ", 1)[1].strip()
        for line in output.splitlines()
        if "attempt " in line
    )

    code, output = run(storage, "resume", attempt_id)

    assert code == 0, output
    assert "no hints" in output


def test_attempts_states_the_limit_when_it_has_no_clock(
    storage: tuple[Path, Path],
) -> None:
    """`practice attempts` lists rows without provisioning a clock, and the honest
    thing to print without one is the limit rather than a countdown from a time
    the listing invented.
    """
    start_code, _ = run(storage, "start", TWO_SUM, "--no-prompt", "--interview")
    assert start_code == 0

    code, output = run(storage, "attempts")

    assert code == 0, output
    assert "15 minute limit" in output


def test_solve_has_no_interview_flag(storage: tuple[Path, Path]) -> None:
    """Deliberate, and the asymmetry is the point rather than an omission.
    Interview mode is about what happens *during* an attempt, and `solve` has no
    during: it opens an attempt, grades the answer already written, and exits.
    """
    code, output = run(storage, "solve", TWO_SUM, "--interview")

    assert code != 0
    assert "--interview" in output


def test_start_names_an_exercise_that_does_not_exist(
    storage: tuple[Path, Path],
) -> None:
    code, output = run(storage, "start", "katas/not-a-real-kata")

    assert code == 2, output
    assert "no exercise with id" in output


def test_start_refuses_an_id_that_is_not_an_exercise_id(
    storage: tuple[Path, Path],
) -> None:
    code, output = run(storage, "start", "NotAnId")

    assert code == 2, output
    assert "kebab-case" in output


# --- attempts --------------------------------------------------------------


def test_attempts_says_so_when_nothing_is_open(storage: tuple[Path, Path]) -> None:
    code, output = run(storage, "attempts")

    assert code == 0, output
    assert "No open attempts." in output


def test_attempts_prints_the_id_in_full(storage: tuple[Path, Path]) -> None:
    """Because that is what `resume` takes. The short form is the workspace
    directory's name and nothing accepts it (PLAN.md §8.1).
    """
    attempt_id = start(storage, TWO_SUM)

    _, output = run(storage, "attempts")

    assert attempt_id in output
    assert len(attempt_id) == 36


def test_attempts_says_which_one_is_current(storage: tuple[Path, Path]) -> None:
    """The one `practice start` or `practice resume` was last run for, which is
    the one `practice mcp` hands a tutor that does not say which (ADR 0026).
    """
    older = start(storage, TWO_SUM)
    newer = start(storage, TWO_SUM)

    _, started_last = run(storage, "attempts")
    run(storage, "resume", older)
    _, resumed_last = run(storage, "attempts")

    assert f"{newer}  Two Sum  (current)" in started_last
    assert f"{older}  Two Sum  (current)" not in started_last
    assert f"{older}  Two Sum  (current)" in resumed_last
    assert f"{newer}  Two Sum  (current)" not in resumed_last


def test_submitting_another_attempt_does_not_take_the_mark(
    storage: tuple[Path, Path], tmp_path: Path
) -> None:
    """`submit` loads the attempt the way `resume` does, on its way to closing
    it. When that marked it, grading one attempt from a terminal made a tutor
    forget which one was being worked on.
    """
    working_on = start(storage, TWO_SUM)
    start(storage, TWO_SUM)
    other = start(storage, TWO_SUM)
    run(storage, "resume", working_on)
    mine = tmp_path / "mine.py"
    mine.write_text(SOLVED, encoding="utf-8")

    code, output = run(storage, "submit", other, "--source", str(mine))
    _, listing = run(storage, "attempts")

    assert code == 0, output
    assert "2 open attempts" in listing
    assert f"{working_on}  Two Sum  (current)" in listing


def test_solve_does_not_take_the_mark(storage: tuple[Path, Path]) -> None:
    """It starts an attempt and finishes it in the same breath, for an author
    checking a reference. Nobody turned to that attempt.
    """
    working_on = start(storage, TWO_SUM)
    start(storage, TWO_SUM)
    run(storage, "resume", working_on)

    code, output = run(storage, "solve", TWO_SUM, "--reference", "--no-prompt")
    _, listing = run(storage, "attempts")

    assert code == 0, output
    assert "2 open attempts" in listing
    assert f"{working_on}  Two Sum  (current)" in listing


def test_attempts_shows_the_history_of_one_exercise(storage: tuple[Path, Path]) -> None:
    """The other question the attempt table can answer, and the reason the
    `history_for` port method had no caller until this phase.
    """
    run(storage, "solve", TWO_SUM, "--reference", "--no-prompt")

    code, output = run(storage, "attempts", "--exercise", TWO_SUM)

    assert code == 0, output
    assert "1 attempt at katas/two-sum." in output
    assert "PASS" in output


def test_attempts_history_is_empty_for_an_exercise_nobody_attempted(
    storage: tuple[Path, Path],
) -> None:
    code, output = run(storage, "attempts", "--exercise", TWO_SUM)

    assert code == 0, output
    assert "No attempts at katas/two-sum." in output


def test_attempts_flags_one_that_can_only_be_abandoned(
    storage: tuple[Path, Path],
) -> None:
    """A workspace collected under a live attempt. The listing says so rather than
    letting `resume` be the thing that finds out.
    """
    attempt_id = start(storage, TWO_SUM)
    workspaces, _ = storage
    for directory in workspaces.iterdir():
        for path in sorted(directory.rglob("*"), reverse=True):
            path.chmod(0o700)
        _remove(directory)

    _, output = run(storage, "attempts")

    assert attempt_id in output
    assert "can only be abandoned" in output


# --- resume ----------------------------------------------------------------


def test_resume_reports_where_the_attempt_stands(storage: tuple[Path, Path]) -> None:
    attempt_id = start(storage, REVERT)

    code, output = run(storage, "resume", attempt_id)

    assert code == 0, output
    assert "0/25 commands" in output
    assert f"practice submit {attempt_id}" in output


def test_resume_runs_more_commands_against_the_same_repository(
    storage: tuple[Path, Path], tmp_path: Path
) -> None:
    """Two invocations, one repository, one event log — which is the whole claim.

    The second `.cmds` file sees the branch the first one created, so the commands
    cannot have run against a freshly provisioned fixture.
    """
    attempt_id = start(storage, REVERT)
    first = tmp_path / "first.cmds"
    first.write_text("git switch -c scratch\n", encoding="utf-8")
    second = tmp_path / "second.cmds"
    second.write_text("git branch --list scratch\n", encoding="utf-8")

    run(storage, "resume", attempt_id, "-c", str(first))
    code, output = run(storage, "resume", attempt_id, "-c", str(second))

    assert code == 0, output
    assert "scratch" in output


def test_the_budget_belongs_to_the_attempt_not_the_invocation(
    storage: tuple[Path, Path], tmp_path: Path
) -> None:
    """The thing that makes this a resumption rather than a second attempt: commands
    run yesterday still count against today's budget.
    """
    attempt_id = start(storage, REVERT)
    commands = tmp_path / "two.cmds"
    commands.write_text("git status\ngit log --oneline\n", encoding="utf-8")

    run(storage, "resume", attempt_id, "-c", str(commands))
    _, output = run(storage, "resume", attempt_id)

    assert "2/25 commands" in output


def test_resume_refuses_commands_for_a_kata(
    storage: tuple[Path, Path], tmp_path: Path
) -> None:
    attempt_id = start(storage, TWO_SUM)
    commands = tmp_path / "x.cmds"
    commands.write_text("git status\n", encoding="utf-8")

    code, output = run(storage, "resume", attempt_id, "-c", str(commands))

    assert code == 2, output
    assert "has no command console" in output


def test_resume_refuses_an_attempt_that_has_been_graded(
    storage: tuple[Path, Path],
) -> None:
    """A `solve` run completes the attempt, so this is the state a stale terminal
    is in. It says `completed`, because "already graded" and "abandoned" send
    someone to different places.
    """
    run(storage, "solve", TWO_SUM, "--reference", "--no-prompt")
    _, listed = run(storage, "attempts", "--exercise", TWO_SUM)
    attempt_id = listed.split()[0]

    code, output = run(storage, "resume", attempt_id)

    assert code == 2, output
    assert "completed" in output


def test_resume_refuses_an_id_that_is_not_an_attempt_id(
    storage: tuple[Path, Path],
) -> None:
    """A different message from "no attempt with that id", because the fixes differ:
    a malformed id is usually a truncated paste.
    """
    code, output = run(storage, "resume", "not-a-uuid")

    assert code == 2, output
    assert "not a valid attempt id" in output
    assert "prints ids in full" in output


def test_resume_refuses_an_attempt_nobody_started(storage: tuple[Path, Path]) -> None:
    code, output = run(storage, "resume", "deadbeef-0000-4000-8000-000000000000")

    assert code == 2, output
    assert "no attempt with id" in output


# --- submit ----------------------------------------------------------------


def test_submit_grades_a_scenario_as_it_was_left(
    storage: tuple[Path, Path], tmp_path: Path
) -> None:
    attempt_id = start(storage, REVERT)
    first = tmp_path / "look.cmds"
    first.write_text("git log --oneline\n", encoding="utf-8")
    second = tmp_path / "fix.cmds"
    second.write_text(
        "git revert --no-edit HEAD\ngit push origin main\n", encoding="utf-8"
    )
    run(storage, "resume", attempt_id, "-c", str(first))
    run(storage, "resume", attempt_id, "-c", str(second))

    code, output = run(storage, "submit", attempt_id)

    assert code == 0, output
    assert "graded the repository as you left it" in output
    # A clean PASS, advisories included, which is a stronger assertion here than
    # the outcome alone. `command_used` reads the *attempt's* log, so the `git log`
    # satisfying "you inspected the repository before changing it" was run by a
    # different process two invocations ago: the log survived them both.
    assert output.rstrip().endswith("PASS")


def test_submit_grades_a_kata_from_a_source_file(
    storage: tuple[Path, Path], tmp_path: Path
) -> None:
    attempt_id = start(storage, TWO_SUM)
    mine = tmp_path / "mine.py"
    mine.write_text(SOLVED, encoding="utf-8")

    code, output = run(
        storage,
        "submit",
        attempt_id,
        "--source",
        str(mine),
        "--time",
        "O(n)",
        "--space",
        "O(n)",
    )

    assert code == 0, output
    assert output.rstrip().endswith("PASS")


def test_submit_exits_one_when_a_required_check_fails(
    storage: tuple[Path, Path],
) -> None:
    """The same exit codes as `solve`, because the thing being reported is the same."""
    attempt_id = start(storage, REVERT)

    code, output = run(storage, "submit", attempt_id)

    assert code == 1, output
    assert "FAIL" in output


def test_submit_refuses_source_for_a_scenario(
    storage: tuple[Path, Path], tmp_path: Path
) -> None:
    attempt_id = start(storage, REVERT)
    mine = tmp_path / "mine.py"
    mine.write_text(SOLVED, encoding="utf-8")

    code, output = run(storage, "submit", attempt_id, "--source", str(mine))

    assert code == 2, output
    assert "graded on the repository as you left it" in output


def test_submit_requires_source_for_a_kata(storage: tuple[Path, Path]) -> None:
    attempt_id = start(storage, TWO_SUM)

    code, output = run(storage, "submit", attempt_id)

    assert code == 2, output
    assert "pass --source FILE" in output


def test_submitting_twice_is_refused(
    storage: tuple[Path, Path], tmp_path: Path
) -> None:
    """A double-clicked submit. The second one is refused before the workspace is
    reached, so the message is about the attempt rather than about a missing
    directory.
    """
    attempt_id = start(storage, TWO_SUM)
    mine = tmp_path / "mine.py"
    mine.write_text(SOLVED, encoding="utf-8")
    run(storage, "submit", attempt_id, "--source", str(mine))

    code, output = run(storage, "submit", attempt_id, "--source", str(mine))

    assert code == 2, output
    assert "completed" in output


# --- abandon ---------------------------------------------------------------


def test_abandon_closes_the_attempt_and_frees_the_workspace(
    storage: tuple[Path, Path],
) -> None:
    attempt_id = start(storage, REVERT)

    code, output = run(storage, "abandon", attempt_id)

    assert code == 0, output
    assert "abandoned" in output
    assert "No open attempts." in run(storage, "attempts")[1]
    assert "No workspaces." in run(storage, "gc")[1]


def test_an_abandoned_attempt_stays_in_the_history(storage: tuple[Path, Path]) -> None:
    """The row stays, marked. An attempt someone walked away from is as much of a
    fact as one they finished.
    """
    attempt_id = start(storage, REVERT)
    run(storage, "abandon", attempt_id)

    _, output = run(storage, "attempts", "--exercise", REVERT)

    assert attempt_id in output
    assert "abandoned" in output


def test_abandoning_twice_is_refused(storage: tuple[Path, Path]) -> None:
    attempt_id = start(storage, TWO_SUM)
    run(storage, "abandon", attempt_id)

    code, output = run(storage, "abandon", attempt_id)

    assert code == 2, output
    assert "abandoned" in output


# --- gc --------------------------------------------------------------------


def test_gc_never_collects_a_workspace_that_is_in_use(
    storage: tuple[Path, Path],
) -> None:
    """The guarantee the command refused to delete anything for three phases over.
    Requested with the flag, so a `discard` loop that ignored the classification
    would fail here.
    """
    attempt_id = start(storage, REVERT)

    code, output = run(storage, "gc", "--no-dry-run")

    assert code == 0, output
    assert "1 in use, 0 orphans" in output
    assert run(storage, "resume", attempt_id)[0] == 0


def test_gc_collects_an_interrupted_provision(storage: tuple[Path, Path]) -> None:
    """A directory with no metadata and no attempt row: what a killed process
    leaves. Collectable because the orphan rule is decided on the directory name.
    """
    workspaces, _ = storage
    (workspaces / "deadbeef").mkdir(parents=True)
    (workspaces / "deadbeef" / "repo").mkdir()

    code, output = run(storage, "gc", "--no-dry-run")

    assert code == 0, output
    assert "collected 1 workspace" in output
    assert not (workspaces / "deadbeef").exists()


def test_gc_reports_an_orphan_without_deleting_it_by_default(
    storage: tuple[Path, Path],
) -> None:
    """`--dry-run` is still the default, and not out of timidity: an orphan means
    something went wrong, and seeing what before deleting it is usually worth the
    second invocation.
    """
    workspaces, _ = storage
    (workspaces / "deadbeef").mkdir(parents=True)

    code, output = run(storage, "gc")

    assert code == 0, output
    assert "1 orphan" in output
    assert "re-run with --no-dry-run" in output
    assert (workspaces / "deadbeef").exists()


def test_gc_says_nothing_has_been_provisioned_yet(storage: tuple[Path, Path]) -> None:
    code, output = run(storage, "gc")

    assert code == 0, output
    assert "No workspace directory yet" in output


def _remove(directory: Path) -> None:
    """Delete a provisioned workspace from a test, read-only git objects and all.

    The same papercut `WorkspaceLayout.destroy` absorbs: git marks loose objects
    read-only and Windows honours that against deletion. Done by hand here because
    the point of the test is a workspace that went away *without* the application
    knowing.
    """

    def force(_function: object, path: str, _exception: BaseException) -> None:
        target = Path(path)
        target.chmod(stat.S_IWRITE | stat.S_IREAD)
        target.rmdir() if target.is_dir() else target.unlink()

    shutil.rmtree(directory, onexc=force)
