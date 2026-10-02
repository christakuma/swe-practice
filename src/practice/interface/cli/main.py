"""The `practice` command.

A second driving adapter over the same core as the web app, which is the point
of it: if the core were secretly coupled to HTTP, this would not work. It also
keeps `practice validate` runnable in CI without booting a server (PLAN.md §2).

Four commands so far. Three of them are in CI, each for a different reason.
`validate` audits the library without running anything. `fixtures` runs every
fixture and checks what it built against `content/fixtures.lock`, which is how
the cross-platform determinism claim is tested rather than asserted. `gc`
reports what is left on disk — and at this phase only reports, because deciding
which workspace is an orphan needs the attempt table (PLAN.md §8.1, Phase 6).

`solve` is the fourth and the first one that is a *product* rather than a tool:
it starts an attempt, grades it and prints the verdict. It is also the reason the
composition root exists — three commands that each built one adapter needed no
wiring module, and this one needs six objects with four edges between them.

**One command for both exercise kinds, dispatching on the kind.** A kata takes
`--source`; a git scenario takes `--commands`, a file of one command per line in
the same `.cmds` format the library's own reference solutions use. The alternative
was `practice solve` and `practice run`, and it is the wrong cut: the thing a
solver is doing is the same — attempt an exercise and get a verdict — and the
kind registry exists so the rest of the system does not have to care which kind it
is. A driving adapter that split on it would be the one place reintroducing the
distinction.

**`solve` does everything in one process, and that is a persistence constraint
rather than a design.** The attempt repository is in memory until Phase 6, so an
attempt cannot outlive the invocation that started it. For a kata that is barely
visible. For a scenario it is the whole difference between replaying a command
list and an interactive console: a console needs `practice start`, `practice run`
and `practice submit` to find the same attempt, which needs the attempt table.
Phase 8's web workbench is where the interactive surface belongs anyway, and
`--commands` is not a stopgap for it — it is how CI grades every reference
solution in the library, through this same code path.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003  (Typer reads this annotation at runtime)
from typing import TYPE_CHECKING, Annotated, Final

import typer

from practice.adapters.content import (
    ExerciseReport,
    FilesystemContentRepository,
    validate_library,
)
from practice.adapters.content.validation import unproven_by_design
from practice.adapters.sandbox import (
    CommandRejectedError,
    SubprocessSandboxProvisioner,
)
from practice.adapters.sandbox.env import ToolNotFoundError
from practice.adapters.sandbox.fixture_lock import (
    LOCK_FILENAME,
    compare,
    fingerprint_library,
    lock_path,
    parse,
    render,
)
from practice.adapters.sandbox.fixture_runner import FixtureError
from practice.application.errors import ApplicationError
from practice.composition import build_services
from practice.config import (
    CONTENT_ROOT_ENV,
    WORKSPACE_ROOT_ENV,
    content_root,
    workspace_root,
)
from practice.domain.attempt import ComplexityClaim
from practice.domain.commands import parse_command_list
from practice.domain.errors import DomainError, InvalidValueError
from practice.domain.exercise import GitScenarioSpec, KataSpec
from practice.domain.ids import ExerciseId
from practice.domain.verdict import Outcome

if TYPE_CHECKING:
    from collections.abc import Mapping

    from practice.adapters.sandbox import WorkspaceRecord
    from practice.application.dto import StartedAttempt, Submission
    from practice.composition import Services
    from practice.domain.attempt import CommandResult
    from practice.domain.verdict import CheckReport

__all__ = ["app", "fixtures", "gc", "solve", "validate"]

app = typer.Typer(
    name="practice",
    help="Offline practice for data-structure katas and operational git.",
    no_args_is_help=True,
    add_completion=False,
)

_OK = "  ok   "
_BAD = "  FAIL "
_NOTE = "  note "
_INDENT = "         "

#: How an outcome reads at the end of a `solve` run, and in what colour. A
#: mapping keyed by the enum rather than a chain of branches, so adding an
#: `Outcome` member without deciding how it prints is a mypy error rather than
#: a `KeyError` in front of a solver.
_OUTCOMES: Final[Mapping[Outcome, str]] = {
    Outcome.PASS: "PASS",
    Outcome.PASS_WITH_ADVISORIES: "PASS, with advisories",
    Outcome.FAIL: "FAIL",
}

_OUTCOME_COLOURS: Final[Mapping[Outcome, str]] = {
    Outcome.PASS: typer.colors.GREEN,
    Outcome.PASS_WITH_ADVISORIES: typer.colors.YELLOW,
    Outcome.FAIL: typer.colors.RED,
}

#: Binary, because the thing being measured is disk usage.
_KB = 1024

#: How many lines of one command's output a scenario transcript shows. Enough
#: for a `git status` or a short `git log`, few enough that a `--all` log
#: cannot push the verdict off the top of a terminal.
_TRANSCRIPT_LINES: Final = 12


@app.callback()
def main() -> None:
    """Offline practice for data-structure katas and operational git."""


@app.command()
def validate(
    content: Annotated[
        Path | None,
        typer.Option(
            "--content-root",
            envvar=CONTENT_ROOT_ENV,
            help="The exercise library to check. Defaults to this project's.",
        ),
    ] = None,
    caveats: Annotated[
        bool,
        typer.Option(
            "--caveats/--no-caveats",
            help="Print what a passing run does not yet prove.",
        ),
    ] = True,
) -> None:
    """Check every exercise on disk, and say what is wrong with the ones that are.

    Exits non-zero if anything is wrong, so CI can depend on it.
    """
    root = content.resolve() if content is not None else content_root()
    report = validate_library(root)

    typer.echo(str(root))
    for problem in report.problems:
        typer.secho(f"{_BAD}{problem}", fg=typer.colors.RED)
    for exercise in report.exercises:
        label = _label(exercise, root)
        if exercise.ok:
            typer.secho(f"{_OK}{label}", fg=typer.colors.GREEN)
            continue
        typer.secho(f"{_BAD}{label}", fg=typer.colors.RED)
        for problem in exercise.problems:
            typer.echo(f"{_INDENT}{problem}")

    typer.echo("")
    typer.echo(_summarise(len(report.exercises), len(report.failures)))

    # Printed on success too. A command that reports "3 exercises, all valid"
    # and stops there invites exactly the misreading PLAN.md §11 warns about —
    # green here is not content that is known to work (§9, §11).
    if caveats and report.ok:
        typer.echo("")
        typer.secho("Not proven by this command:", fg=typer.colors.YELLOW)
        for caveat in unproven_by_design():
            typer.echo(f"  - {caveat}")

    if not report.ok:
        raise typer.Exit(code=1)


@app.command()
def fixtures(
    content: Annotated[
        Path | None,
        typer.Option(
            "--content-root",
            envvar=CONTENT_ROOT_ENV,
            help="The exercise library to fingerprint. Defaults to this project's.",
        ),
    ] = None,
    write: Annotated[
        bool,
        typer.Option(
            "--write/--check",
            help=f"Rewrite {LOCK_FILENAME}, or check it and exit non-zero on a diff.",
        ),
    ] = False,
) -> None:
    """Run every fixture and check what it built against the lock file.

    `--check` is what CI runs, on Linux and on Windows, and a disagreement
    between the two is the whole point: identical hashes on every platform is
    the Phase 3 exit criterion, and this is the thing that tests it.

    `--write` is what you run after editing a fixture. Review the diff — an
    unexpected line in it means the edit changed more history than you thought.
    """
    root = content.resolve() if content is not None else content_root()
    lock = lock_path(root)

    try:
        found = fingerprint_library(
            FilesystemContentRepository(root).list_exercises(), content_root=root
        )
    except ToolNotFoundError as exc:
        typer.secho(f"cannot run fixtures: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc
    except FixtureError as exc:
        typer.secho(f"a fixture failed:\n{exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.echo(lock)
    if write:
        lock.write_text(render(found), encoding="utf-8", newline="")
        typer.secho(
            f"{_OK}wrote {len(found)} fixture fingerprints", fg=typer.colors.GREEN
        )
        return

    if not lock.is_file():
        typer.secho(
            f"{_BAD}{LOCK_FILENAME} does not exist; create it with "
            f"`practice fixtures --write`",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    problems = compare(parse(lock.read_text(encoding="utf-8")), found)
    for problem in problems:
        typer.secho(f"{_BAD}{problem}", fg=typer.colors.RED)
    if problems:
        typer.echo("")
        typer.secho(
            "Fixtures no longer match the lock file. If you changed one, "
            "regenerate with `practice fixtures --write` and review the diff. "
            "If you did not, the pinned environment has broken, or git has "
            "changed how it hashes.",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=1)

    for fingerprint in found:
        typer.secho(
            f"{_OK}{fingerprint.exercise_id} "
            f"({len(fingerprint.aliases)} commits, {len(fingerprint.refs)} refs)",
            fg=typer.colors.GREEN,
        )
    typer.echo("")
    typer.echo(f"{len(found)} {_plural('fixture', len(found))} match {LOCK_FILENAME}.")


@app.command()
def gc(
    workspaces: Annotated[
        Path | None,
        typer.Option(
            "--workspace-root",
            envvar=WORKSPACE_ROOT_ENV,
            help="Where attempt workspaces live. Defaults to the user cache.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--no-dry-run",
            help="Only report. Deleting needs the attempt table (phase 6).",
        ),
    ] = True,
) -> None:
    """Report the attempt workspaces left on disk.

    **It never deletes anything at this phase, and that is deliberate.** An
    orphan is defined precisely in PLAN.md §8.1 as *a workspace directory with
    no corresponding `active` attempt row* — and there is no attempt table until
    Phase 6. Without one, "collect orphans" would happily delete the workspace
    of a session you have open in another tab, which is a far worse outcome than
    a cache directory that is temporarily larger than it needs to be.
    """
    if not dry_run:
        typer.secho(
            "--no-dry-run is refused: an orphan is a workspace with no active "
            "attempt row, and the attempt table lands in phase 6. Until then gc "
            "can see the workspaces but not which of them are still in use, so "
            "it reports and never deletes (PLAN.md 8.1).",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=2)

    root = workspaces.resolve() if workspaces is not None else workspace_root()
    provisioner = SubprocessSandboxProvisioner(
        content_root=content_root(), workspace_root=root
    )
    found = provisioner.workspaces()

    typer.echo(root)
    if not root.is_dir():
        typer.echo("")
        typer.echo("No workspace directory yet; nothing has been provisioned.")
        return

    for record in found:
        typer.echo(f"  {_describe(record)}")

    typer.echo("")
    total = sum(record.size_bytes() for record in found)
    typer.echo(
        f"{len(found)} {_plural('workspace', len(found))}, {_size(total)}."
        if found
        else "No workspaces."
    )
    if found:
        typer.secho(
            "Nothing deleted: which of these is an orphan needs the attempt "
            "table (phase 6). Until then, an attempt disposes of its own "
            "workspace when it is submitted or abandoned.",
            fg=typer.colors.YELLOW,
        )


@app.command()
def solve(
    exercise: Annotated[
        str,
        typer.Argument(
            help="The exercise id, e.g. katas/two-sum.",
            metavar="EXERCISE_ID",
        ),
    ],
    source: Annotated[
        Path | None,
        typer.Option(
            "--source",
            "-s",
            help="Kata: the file holding your solution. Defaults to the stub.",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    commands: Annotated[
        Path | None,
        typer.Option(
            "--commands",
            "-c",
            help="Git scenario: a file of git commands, one per line.",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    reference: Annotated[
        bool,
        typer.Option(
            "--reference",
            help="Grade the exercise's own reference solution instead.",
        ),
    ] = False,
    time: Annotated[
        str | None,
        typer.Option("--time", help="Your claimed time complexity, e.g. O(n)."),
    ] = None,
    space: Annotated[
        str | None,
        typer.Option("--space", help="Your claimed space complexity, e.g. O(n)."),
    ] = None,
    prompt: Annotated[
        bool,
        typer.Option("--prompt/--no-prompt", help="Print the exercise prompt first."),
    ] = True,
    content: Annotated[
        Path | None,
        typer.Option(
            "--content-root",
            envvar=CONTENT_ROOT_ENV,
            help="The exercise library to solve from. Defaults to this project's.",
        ),
    ] = None,
    workspaces: Annotated[
        Path | None,
        typer.Option(
            "--workspace-root",
            envvar=WORKSPACE_ROOT_ENV,
            help="Where to provision the attempt. Defaults to the user cache.",
        ),
    ] = None,
) -> None:
    """Solve an exercise from the terminal: grade an answer and print the verdict.

    Exits 0 when the attempt passes -- including a pass with advisories, because
    the goal was met either way -- 1 when a required check fails, and 2 when the
    attempt could not be run at all.

    A **kata** takes `--source`, and with neither `--source` nor `--reference`
    grades the exercise's own stub. A deliberate default rather than a quirk: the
    first thing worth seeing is the hidden suite failing on an unimplemented
    function, which is the same property PLAN.md §9 requires of every kata.

    A **git scenario** takes `--commands`: a file of commands, one per line, in the
    same format as the library's own `.cmds` files. Every line goes through the real
    command policy, so a line the exercise does not allow is refused here exactly as
    it would be in the web console. With `--reference` it replays the exercise's own
    solution, which is also how CI grades it.

        practice solve git/revert-a-pushed-commit --reference
        practice solve git/revert-a-pushed-commit -c my-attempt.cmds
    """
    chosen = [
        name
        for name, given in (
            ("--source", source is not None),
            ("--commands", commands is not None),
            ("--reference", reference),
        )
        if given
    ]
    if len(chosen) > 1:
        typer.secho(
            f"{' and '.join(chosen)} each name an answer to grade; pick one.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)

    library = content.resolve() if content is not None else content_root()
    services = build_services(
        content=library,
        workspaces=workspaces.resolve() if workspaces is not None else None,
    )

    try:
        exercise_id = ExerciseId(exercise)
    except InvalidValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    claim = _claim(time, space)

    try:
        started = services.start_attempt(exercise_id)
    except ApplicationError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    typer.secho(f"{started.exercise.id}  {started.exercise.title}", bold=True)
    if prompt:
        typer.echo("")
        typer.echo(started.exercise.prompt.strip())
    typer.echo("")

    _require_flags_for_kind(started, source=source, commands=commands, complexity=claim)

    try:
        if isinstance(started.exercise.spec, GitScenarioSpec):
            submission, origin = _solve_scenario(
                services, started, library, commands=commands, reference=reference
            )
        else:
            submission, origin = _solve_kata(
                services,
                started,
                library,
                source=source,
                reference=reference,
                complexity=claim,
            )
    except (
        ApplicationError,
        CommandRejectedError,
        DomainError,
        OSError,
    ) as exc:
        # Four error families and one exit code, which is the driving adapter's
        # whole job here: a refusal is a refusal whether it came from the
        # application (nothing to grade), the domain (not a command, or outside
        # the budget), the sandbox's policy (not an allowed program), or the
        # filesystem. `CommandRejectedError` is on the list because it is none of
        # the other three -- and without it a disallowed line reached the user as
        # a traceback, which a test found.
        #
        # The workspace is deliberately left on disk. The attempt is still
        # active, so §8.1 says its workspace lives; disposing of it here would
        # destroy the only thing that could explain the failure -- which for a
        # scenario is a repository the solver built -- and `practice gc` already
        # reports it.
        typer.secho(f"cannot grade this attempt: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    typer.echo("")
    typer.echo(f"graded {origin}")
    typer.echo("")
    _report_verdict(submission)

    if not submission.passed:
        raise typer.Exit(code=1)


def _solve_kata(
    services: Services,
    started: StartedAttempt,
    library: Path,
    *,
    source: Path | None,
    reference: bool,
    complexity: ComplexityClaim | None,
) -> tuple[Submission, str]:
    """Grade a kata: one source file, one hidden suite, one verdict."""
    text, origin = _solution_source(
        started, library, source=source, reference=reference
    )
    return services.submit_solution(
        started.attempt.id, text, complexity=complexity
    ), origin


def _solve_scenario(
    services: Services,
    started: StartedAttempt,
    library: Path,
    *,
    commands: Path | None,
    reference: bool,
) -> tuple[Submission, str]:
    """Replay a command list through the real policy, then grade the repository.

    Each line is echoed with what it did before the next one runs, so a replay
    reads as a transcript rather than as a wall of output followed by a verdict.
    That matters most when a line fails: `git revert` hitting a conflict is often
    the most instructive thing in an attempt, and a transcript shows *where* the
    attempt went sideways.
    """
    spec = started.exercise.spec
    if not isinstance(spec, GitScenarioSpec):  # pragma: no cover - dispatched above
        raise ApplicationError(f"{started.exercise.id} is not a git scenario")

    if commands is None and not reference:
        typer.secho(
            f"{started.exercise.id} is a git scenario: pass --commands FILE with "
            f"the commands to run, or --reference to replay the exercise's own "
            f"solution. There is no interactive console yet (phase 8).",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)

    if commands is not None:
        text, origin = commands.read_text(encoding="utf-8"), str(commands)
    else:
        path = library / started.exercise.id.value / spec.reference
        text, origin = (
            path.read_text(encoding="utf-8"),
            f"{spec.reference} (the exercise's own)",
        )

    run = services.run_scenario_command
    for command in parse_command_list(text):
        result = run(started.attempt.id, command.text).command.result
        typer.secho(
            f"{_command_marker(result)}$ {command.text}",
            fg=_command_colour(result),
        )
        for line in _transcript(result):
            typer.echo(f"{_INDENT}{line}")

    return services.submit_scenario(started.attempt.id), origin


def _require_flags_for_kind(
    started: StartedAttempt,
    *,
    source: Path | None,
    commands: Path | None,
    complexity: ComplexityClaim | None,
) -> None:
    """Refuse a flag that belongs to the other exercise kind.

    One guard before dispatch rather than a check inside each branch, so the two
    kinds cannot drift into refusing different things -- and so the message always
    names the kind the exercise actually is, which is the fact the solver got wrong.

    Checked after the attempt has started rather than before, because the kind is not
    known until the exercise is loaded. The cost is a workspace that `practice gc`
    reports, which is cheaper than teaching the CLI to parse the content library
    before it parses its own arguments.
    """
    scenario = isinstance(started.exercise.spec, GitScenarioSpec)
    wrong = [
        name
        for name, given, belongs_to_scenario in (
            ("--commands", commands is not None, True),
            ("--source", source is not None, False),
            ("--time/--space", complexity is not None, False),
        )
        if given and belongs_to_scenario is not scenario
    ]
    if not wrong:
        return

    takes = "--commands" if scenario else "--source"
    typer.secho(
        f"{started.exercise.id} is a {started.exercise.kind.value}: it takes "
        f"{takes}, not {' or '.join(wrong)}.",
        fg=typer.colors.RED,
    )
    raise typer.Exit(code=2)


def _command_marker(result: CommandResult) -> str:
    """The exit code rather than `FAIL`, and the distinction matters here.

    A non-zero command is not a wrong answer. `git revert` hitting a conflict and
    `git push` being rejected are both things an attempt is *supposed* to run into,
    and marking them the way a failed check is marked would tell a solver they had
    made a mistake at the exact moment they had not. The code is also what someone
    who has used a shell is already reading for.
    """
    return _OK if result.succeeded else f"  {result.exit_code:>4} "


def _command_colour(result: CommandResult) -> str:
    return typer.colors.GREEN if result.succeeded else typer.colors.YELLOW


def _transcript(result: CommandResult) -> tuple[str, ...]:
    """What a command printed, capped so one `git log` cannot bury the verdict.

    stderr first when the command failed, because that is where the reason is. The
    cap is on lines rather than bytes: the sandbox already caps bytes, and what
    makes a transcript unreadable is length rather than size.
    """
    streams = (
        (result.stderr, result.stdout)
        if not result.succeeded
        else (result.stdout, result.stderr)
    )
    lines = [line for stream in streams for line in stream.splitlines() if line]
    if len(lines) <= _TRANSCRIPT_LINES:
        return tuple(lines)
    hidden = len(lines) - _TRANSCRIPT_LINES
    return (*lines[:_TRANSCRIPT_LINES], f"... {hidden} more line(s)")


def _solution_source(
    started: StartedAttempt,
    library: Path,
    *,
    source: Path | None,
    reference: bool,
) -> tuple[str, str]:
    """The source to grade, and a phrase saying where it came from.

    The stub and the reference are read from the content directory rather than
    from the workspace, even though the stub is copied into one. The workspace
    is where a solution *runs*; the library is where the exercise's own files
    live, and the reference is deliberately never copied in at all -- it is an
    answer key, and the provisioner leaves it behind.
    """
    if source is not None:
        return source.read_text(encoding="utf-8"), str(source)

    spec = started.exercise.spec
    if not isinstance(spec, KataSpec):  # pragma: no cover - the registry refuses first
        message = f"{started.exercise.id} has no stub to fall back to"
        raise ApplicationError(message)

    name = spec.reference if reference else spec.stub
    text = (library / started.exercise.id.value / name).read_text(encoding="utf-8")
    return text, f"{name} (the exercise's own)"


def _claim(time: str | None, space: str | None) -> ComplexityClaim | None:
    """Both axes or neither.

    A claim about one axis cannot disagree with an expectation that has two,
    which is why `ComplexityClaim` refuses to hold one (PLAN.md §4.3) -- so half
    a pair is a usage error rather than something to pad with a guess. Checked
    before the attempt is started, so a typo does not leave a workspace behind.
    """
    if time is None and space is None:
        return None
    if time is None or space is None:
        typer.secho(
            "--time and --space go together: a claim about one axis cannot "
            "disagree with an expectation about two.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)
    return ComplexityClaim(time=time, space=space)


def _report_verdict(submission: Submission) -> None:
    """Every check, then the outcome.

    Printed in the order the verdict holds them, which for a kata is the order
    the hidden suite declared its tests -- so two runs of the same solution read
    the same way down the page.

    What is repeated under the outcome is whatever has to change next: the
    failures when there are any, and the advisories when there are not. The
    outcome line is where someone stops reading, and a nine-test kata pushes
    the first failure off the top of a short terminal — while listing
    advisories under a FAIL would bury the thing that actually failed.
    """
    for report in submission.verdict.reports:
        _report_check(report)

    typer.echo("")
    typer.secho(_OUTCOMES[submission.outcome], fg=_OUTCOME_COLOURS[submission.outcome])
    outstanding = (
        submission.verdict.advisories
        if submission.passed
        else submission.verdict.failures
    )
    for report in outstanding:
        typer.echo(f"  - {report.label}")


def _report_check(report: CheckReport) -> None:
    """One check. Failures carry their detail; a pass is one line."""
    if report.passed:
        typer.secho(f"{_OK}{report.label}", fg=typer.colors.GREEN)
        return

    marker = _BAD if report.is_required else _NOTE
    colour = typer.colors.RED if report.is_required else typer.colors.YELLOW
    typer.secho(f"{marker}{report.label}", fg=colour)
    if report.expected is not None and report.actual is not None:
        typer.echo(f"{_INDENT}expected {report.expected}, got {report.actual}")
    for line in (report.explanation or "").strip().splitlines():
        typer.echo(f"{_INDENT}{line}")


def _describe(record: WorkspaceRecord) -> str:
    """One workspace, on one line.

    An undescribed workspace is called out rather than skipped: it means a
    provision was interrupted before it wrote its metadata, which is precisely
    the kind of leftover worth knowing about.
    """
    if not record.is_described:
        return (
            f"{record.short_id}  (no readable metadata: an interrupted "
            f"provision)  {_size(record.size_bytes())}"
        )
    return (
        f"{record.short_id}  {record.exercise_id}  "
        f"{record.created_at}  {_size(record.size_bytes())}"
    )


def _label(exercise: ExerciseReport, root: Path) -> str:
    """The id, or the directory relative to the root when the id is unreadable.

    The root is already the first line of output, so repeating an absolute path
    on every heading is noise — and the absolute path of a temp directory in CI
    is worse than noise.
    """
    return exercise.exercise_id or exercise.directory.relative_to(root).as_posix()


def _plural(noun: str, count: int) -> str:
    return noun if count == 1 else f"{noun}s"


def _size(total: int) -> str:
    """A size a human can read, which is the only reason gc prints one."""
    if total < _KB:
        return f"{total} B"
    if total < _KB * _KB:
        return f"{total / _KB:.0f} KB"
    return f"{total / (_KB * _KB):.1f} MB"


def _summarise(total: int, failed: int) -> str:
    exercises = "exercise" if total == 1 else "exercises"
    if not total:
        return "No exercises found."
    if not failed:
        return f"{total} {exercises}, all valid."
    verb = "has" if failed == 1 else "have"
    return f"{failed} of {total} {exercises} {verb} problems."
