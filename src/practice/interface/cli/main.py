"""The `practice` command.

A second driving adapter over the same core as the web app, which is the point
of it: if the core were secretly coupled to HTTP, this would not work. It also
keeps `practice validate` runnable in CI without booting a server (PLAN.md §2).

Three commands so far, and each one is in CI for a different reason.
`validate` audits the library without running anything. `fixtures` runs every
fixture and checks what it built against `content/fixtures.lock`, which is how
the cross-platform determinism claim is tested rather than asserted. `gc`
reports what is left on disk — and at this phase only reports, because deciding
which workspace is an orphan needs the attempt table (PLAN.md §8.1, Phase 6).
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003  (Typer reads this annotation at runtime)
from typing import TYPE_CHECKING, Annotated

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
from practice.config import (
    CONTENT_ROOT_ENV,
    WORKSPACE_ROOT_ENV,
    content_root,
    workspace_root,
)

if TYPE_CHECKING:
    from practice.adapters.sandbox import WorkspaceRecord

__all__ = ["app", "fixtures", "gc", "validate"]

app = typer.Typer(
    name="practice",
    help="Offline practice for data-structure katas and operational git.",
    no_args_is_help=True,
    add_completion=False,
)

_OK = "  ok   "
_BAD = "  FAIL "
_INDENT = "         "

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
