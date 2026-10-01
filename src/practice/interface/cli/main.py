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
it starts an attempt, grades a solution and prints the verdict. It is also the
reason the composition root exists — three commands that each built one adapter
needed no wiring module, and this one needs six objects with four edges between
them.

**`solve` does everything in one process, and that is a Phase 4 constraint
rather than a design.** The attempt repository is in memory until Phase 6, so an
attempt cannot outlive the invocation that started it; splitting this into
`practice start` and `practice submit` has to wait for the attempt table, and
offering those now would mean a `submit` that could never find its attempt.
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
from practice.adapters.sandbox import SubprocessSandboxProvisioner
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
from practice.domain.errors import InvalidValueError
from practice.domain.exercise import KataSpec
from practice.domain.ids import ExerciseId
from practice.domain.verdict import Outcome

if TYPE_CHECKING:
    from collections.abc import Mapping

    from practice.adapters.sandbox import WorkspaceRecord
    from practice.application.dto import StartedAttempt, Submission
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
        typer.secho("Not proven at this phase:", fg=typer.colors.YELLOW)
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
            help="The file holding your solution. Defaults to the exercise's stub.",
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
    """Solve a kata from the terminal: grade a solution and print the verdict.

    Exits 0 when the attempt passes -- including a pass with advisories, because
    the goal was met either way -- 1 when a required check fails, and 2 when the
    attempt could not be run at all.

    With neither `--source` nor `--reference`, the exercise's own stub is graded.
    A deliberate default rather than a quirk: the first thing worth seeing is the
    hidden suite failing on an unimplemented function, which is the same property
    PLAN.md §9 requires of every kata in the library.
    """
    if source is not None and reference:
        typer.secho(
            "--source and --reference both name a solution; pick one.",
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

    try:
        text, origin = _solution_source(
            started, library, source=source, reference=reference
        )
        submission = services.submit_solution(
            started.attempt.id, text, complexity=claim
        )
    except (ApplicationError, OSError) as exc:
        # The workspace is deliberately left on disk. The attempt is still
        # active, so §8.1 says its workspace lives; disposing of it here would
        # destroy the only thing that could explain the failure, and `practice
        # gc` already reports it.
        typer.secho(f"cannot grade this attempt: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    typer.echo(f"graded {origin}")
    typer.echo("")
    _report_verdict(submission)

    if not submission.passed:
        raise typer.Exit(code=1)


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
