"""The `practice` command.

A second driving adapter over the same core as the web app, which is the point
of it: if the core were secretly coupled to HTTP, this would not work. It also
keeps `practice validate` runnable in CI without booting a server (PLAN.md §2).

Phase 2 ships one command. The `@app.callback` is what stops Typer collapsing a
single-command app into a bare `practice`, so the invocation is `practice
validate` from the first release rather than changing shape when `gc` and `run`
arrive.
"""

from __future__ import annotations

from pathlib import Path  # noqa: TC003  (Typer reads this annotation at runtime)
from typing import Annotated

import typer

from practice.adapters.content import ExerciseReport, validate_library
from practice.adapters.content.validation import unproven_by_design
from practice.config import CONTENT_ROOT_ENV, content_root

__all__ = ["app", "validate"]

app = typer.Typer(
    name="practice",
    help="Offline practice for data-structure katas and operational git.",
    no_args_is_help=True,
    add_completion=False,
)

_OK = "  ok   "
_BAD = "  FAIL "
_INDENT = "         "


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


def _label(exercise: ExerciseReport, root: Path) -> str:
    """The id, or the directory relative to the root when the id is unreadable.

    The root is already the first line of output, so repeating an absolute path
    on every heading is noise — and the absolute path of a temp directory in CI
    is worse than noise.
    """
    return exercise.exercise_id or exercise.directory.relative_to(root).as_posix()


def _summarise(total: int, failed: int) -> str:
    exercises = "exercise" if total == 1 else "exercises"
    if not total:
        return "No exercises found."
    if not failed:
        return f"{total} {exercises}, all valid."
    verb = "has" if failed == 1 else "have"
    return f"{failed} of {total} {exercises} {verb} problems."
