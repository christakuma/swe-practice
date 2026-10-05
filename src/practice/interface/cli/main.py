"""The `practice` command.

A second driving adapter over the same core as the web app, which is the point
of it: if the core were secretly coupled to HTTP, this would not work. It also
keeps `practice validate` runnable in CI without booting a server (PLAN.md §2).

Eleven commands, in four groups.

**One front door.** `up` is the command a stranger runs: it checks what a fresh
machine is missing, migrates the database, opens a browser and then serves. It
exists because `serve` deliberately does none of that, and the difference is
recorded in ADR 0017 -- `serve` starting a server and nothing else is a property
the test suite depends on (`test_building_the_app_reads_no_database`), so the
setup went into a second command rather than into that one.

**Four tools, three of them in CI, each for a different reason.** `validate`
audits the library without running anything. `fixtures` runs every fixture and
checks what it built against `content/fixtures.lock`, which is how the
cross-platform determinism claim is tested rather than asserted. `gc` reports
the workspaces left on disk — and as of Phase 6 can collect them, because an
orphan is *a workspace directory with no corresponding `active` attempt row*
(PLAN.md §8.1) and there is finally a table to ask.

`pack` is Phase 16's, and the one tool here aimed at somebody other than the
author: it exports the library as a single verifiable file, checks one that
arrived, and installs one as a content root. It is not in CI, because what it
would be testing is covered twice over already — `tests/content/test_pack.py`
round-trips the real library, and the two commands above are what the installed
root is then held to.

**`solve`**, the first command that is a *product* rather than a tool: it starts an
attempt, grades it and prints the verdict. It is also the reason the composition
root exists — three commands that each built one adapter needed no wiring module,
and this one needs six objects with four edges between them.

**Five about the lifecycle**, which only became possible in Phase 6: `start`,
`attempts`, `resume`, `submit` and `abandon`. `start` is the one that makes the
others worth having: an attempt it opens outlives
the process, so `resume` and `submit` can be separate invocations against the same
repository and the same event log. `attempts` plus `resume`/`abandon` is the
resume-or-abandon prompt §8.1 requires, in the form a terminal can have one: a list
and two commands rather than an interactive question, because a CLI that blocked on
a prompt would be unusable from a script and `solve` would no longer work in CI.

**An attempt is named by its full uuid, not by the short id.** `attempts` prints
ids in full for exactly that reason. Accepting a prefix would need a
`find_by_prefix` on the `AttemptRepository` port, which is a method added for one
command's ergonomics and a query nothing else wants — PLAN.md §13's rule is that
an abstraction has to earn its keep. The web app is where the id is in a link
nobody types, and as of phase 7 that link exists.

**One command for both exercise kinds, dispatching on the kind.** A kata takes
`--source`; a git scenario takes `--commands`, a file of one command per line in
the same `.cmds` format the library's own reference solutions use. The alternative
was `practice solve` and `practice run`, and it is the wrong cut: the thing a
solver is doing is the same — attempt an exercise and get a verdict — and the
kind registry exists so the rest of the system does not have to care which kind it
is. A driving adapter that split on it would be the one place reintroducing the
distinction.

**`solve` still does everything in one process, and that is now a choice rather
than a constraint.** It used to be the latter — the attempt repository was in
memory, so an attempt could not outlive the invocation that started it. The
attempt table removes that, and `solve` is unchanged, because one command for one
answer is the right shape for the batch path: it is how CI grades every reference
solution in the library, and a command that needed three invocations to do it
would be worse at that job. Picking an attempt up across processes is what
`resume` and `submit` are for, and the two paths share every use case underneath.
"""

from __future__ import annotations

from importlib.metadata import version

# Imported at runtime, not under TYPE_CHECKING: Typer reads these annotations
# when it builds the commands. It carried a `noqa: TC003` for that until Phase
# 16, when `pack` gave the module a runtime `Path(...)` call and the rule
# stopped firing on its own. If that call ever goes, the suppression comes back
# rather than the import moving.
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Final

import typer
import uvicorn

from practice.adapters.content import (
    PACK_SUFFIX,
    ContentError,
    ExerciseReport,
    FilesystemContentRepository,
    PackContentRepository,
    install_pack,
    verify_pack,
    write_pack,
)
from practice.adapters.content.validation import unproven_by_design, validate_library
from practice.adapters.sandbox import CommandRejectedError, open_in_browser
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
    DATABASE_PATH_ENV,
    WORKSPACE_ROOT_ENV,
    content_root,
    database_path,
    scheduler_name,
    workspace_root,
)
from practice.domain.attempt import AttemptMode, ComplexityClaim
from practice.domain.commands import parse_command_list
from practice.domain.errors import DomainError, InvalidValueError
from practice.domain.exercise import (
    Difficulty,
    ExerciseFilter,
    ExerciseKind,
    GitScenarioSpec,
    editable_source,
)
from practice.domain.ids import AttemptId, ExerciseId
from practice.domain.verdict import Outcome
from practice.interface.cli.launcher import prepare
from practice.interface.web import create_app
from practice.interface.web.security import NotLoopbackError, require_loopback

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime

    from practice.application.dto import (
        Collection,
        OpenAttempt,
        StartedAttempt,
        Submission,
        WorkspaceState,
    )
    from practice.application.use_cases import ResumeAttempt
    from practice.composition import Services
    from practice.domain.attempt import Attempt, CommandResult
    from practice.domain.verdict import CheckReport

__all__ = [
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "abandon",
    "app",
    "attempts",
    "fixtures",
    "gc",
    "pack",
    "resume",
    "serve",
    "solve",
    "start",
    "submit",
    "up",
    "validate",
]

app = typer.Typer(
    name="practice",
    help="Offline practice for data-structure katas and operational git.",
    no_args_is_help=True,
    add_completion=False,
)

#: Where `practice serve` binds. 127.0.0.1 rather than `localhost`, because the
#: name resolves and the literal does not -- and resolution is what the Host
#: check in `interface/web/security.py` exists to defend against.
DEFAULT_HOST: Final = "127.0.0.1"

#: Chosen to be memorable and unlikely to collide with a dev server someone is
#: already running. Nothing depends on it; the cross-origin guard compares the
#: port it actually arrived on.
DEFAULT_PORT: Final = 8765

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


def _show_version(requested: bool) -> None:
    """Print the installed version and stop, before any command runs.

    Read from the package metadata rather than from a constant in this module,
    so `pyproject.toml` is the only place a version number is written. The
    alternative — a `__version__` here — is two numbers that agree until the
    day somebody bumps one of them.

    `PackageNotFoundError` is not caught. It means `practice` is being run
    against a source tree that was never installed, in which case the editable
    install is broken and every other command is about to fail in a less
    informative way.
    """
    if requested:
        typer.echo(f"practice {version('swe-practice')}")
        raise typer.Exit


@app.callback()
def main(
    _version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_show_version,
            is_eager=True,
            help="Print the version and exit.",
        ),
    ] = False,
) -> None:
    """Offline practice for data-structure katas and operational git."""


@app.command()
def up(
    host: Annotated[
        str,
        typer.Option(
            "--host",
            help="Must be a loopback address. Anything else is refused.",
        ),
    ] = DEFAULT_HOST,
    port: Annotated[
        int,
        typer.Option("--port", help="The port to listen on."),
    ] = DEFAULT_PORT,
    open_browser: Annotated[
        bool,
        typer.Option(
            "--open/--no-open",
            help="Open your browser on the app. --no-open for a headless box.",
        ),
    ] = True,
    content: Annotated[
        Path | None,
        typer.Option(
            "--content-root",
            envvar=CONTENT_ROOT_ENV,
            help="The exercise library to serve. Defaults to this project's.",
        ),
    ] = None,
    workspaces: Annotated[
        Path | None,
        typer.Option(
            "--workspace-root",
            envvar=WORKSPACE_ROOT_ENV,
            help="Where attempts are provisioned. Defaults to the user cache.",
        ),
    ] = None,
    db: Annotated[
        Path | None,
        typer.Option(
            "--database",
            envvar=DATABASE_PATH_ENV,
            help="The attempt database. Defaults to the user data directory.",
        ),
    ] = None,
) -> None:
    """Set this machine up, open a browser, and serve. The one command to run.

    **The front door, and `serve` is now the plumbing behind it.** Phase 12's
    exit criterion is that a stranger can clone this and be practising in two
    minutes, and `serve` could not meet it: it starts a server and nothing else,
    on purpose, so the three things a fresh machine is missing -- git, the
    directories, a migrated database -- were each discovered later, inside an
    HTTP request, as a 500 with no instruction in it. This command asks all of
    those up front while there is still a terminal to answer in, then hands over
    to the same `uvicorn.run` (ADR 0017).

    **It refuses rather than serving degraded.** Every step `prepare` runs is a
    prerequisite with no fallback behind it: with no git there is no fixture, with
    no library there is nothing to offer, with no database an attempt cannot be
    saved. A server that booted anyway would be a tool that looks fine until the
    moment you have done the work, which is the failure this whole command exists
    to move earlier. Exit 2, matching every other "this invocation cannot be
    satisfied" in the CLI.

    **The browser is opened before `uvicorn.run`, not after, because there is no
    after** -- `run` blocks until Ctrl-C. So the tab races the server coming up,
    and loses sometimes; what makes that acceptable is that the loser is a
    reload. The alternatives are a thread that waits on the port and a uvicorn
    lifespan hook, and both are real machinery for an outcome the solver can
    reach by pressing F5.
    """
    bind = _bound(host)
    library = content.resolve() if content is not None else content_root()
    provisioned = workspaces.resolve() if workspaces is not None else workspace_root()
    storage = db.resolve() if db is not None else database_path()

    scheduler = scheduler_name()
    first_run = prepare(
        content=library,
        workspaces=provisioned,
        database=storage,
        scheduler=scheduler,
    )
    # Padded to the widest label so the paths form a column. Five lines of
    # ragged left margin is the difference between a report and a dump.
    width = max(len(step.label) for step in first_run.steps)
    for step in first_run.steps:
        marker = _OK if step.ok else _BAD
        colour = typer.colors.GREEN if step.ok else typer.colors.RED
        typer.secho(f"{marker}{step.label:<{width}}", fg=colour, nl=False)
        typer.echo(f"  {step.detail}")
    if not first_run.ok:
        typer.echo("")
        for step in first_run.blockers:
            typer.secho(f"{_BAD}{step.problem}", fg=typer.colors.RED)
        raise typer.Exit(code=2)

    if first_run.fresh:
        typer.echo("")
        typer.echo(f"First run: your attempt history now lives at {storage}.")

    url = f"http://{bind}:{port}"
    typer.echo("")
    typer.echo(url)
    typer.echo("")
    typer.echo("Offline: every asset is served from disk, and nothing is fetched.")
    if open_browser:
        refusal = open_in_browser(url)
        if refusal is not None:
            typer.secho(f"{_NOTE}{refusal}", fg=typer.colors.YELLOW)
    _listen(
        build_services(content=library, workspaces=provisioned, database=storage),
        bind,
        port,
    )


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
    typer.echo(
        _summarise(len(report.exercises), len(report.failures), len(report.problems))
    )

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
def pack(
    out: Annotated[
        Path | None,
        typer.Option(
            "--out",
            help=f"Write a pack here. Defaults to ./library{PACK_SUFFIX}.",
        ),
    ] = None,
    check: Annotated[
        Path | None,
        typer.Option(
            "--check",
            help="Verify an existing pack and list what is in it, instead of "
            "writing one.",
        ),
    ] = None,
    install: Annotated[
        Path | None,
        typer.Option(
            "--install",
            help="Unpack a verified pack into a content root, instead of writing one.",
        ),
    ] = None,
    into: Annotated[
        Path | None,
        typer.Option("--into", help="Where --install puts the library."),
    ] = None,
    content: Annotated[
        Path | None,
        typer.Option(
            "--content-root",
            envvar=CONTENT_ROOT_ENV,
            help="The exercise library to export. Defaults to this project's.",
        ),
    ] = None,
    kinds: Annotated[
        list[ExerciseKind] | None,
        typer.Option("--kind", help="Export only this kind. Repeatable."),
    ] = None,
    difficulties: Annotated[
        list[Difficulty] | None,
        typer.Option("--difficulty", help="Export only this difficulty. Repeatable."),
    ] = None,
) -> None:
    """Export the library as one file, check one, or install one.

    Three modes on one command rather than three commands, which is the shape
    `fixtures` already uses for `--check`/`--write`: they are one subject read
    three ways, and `practice export`, `practice verify` and `practice install`
    would put three unrelated verbs in `--help` for one noun.

    **`--check` is the mode worth running on a pack somebody sent you.** It
    hashes every file against the manifest and then opens the pack through the
    real `ContentRepository`, so a pass means both that the archive arrived
    intact and that the library inside it loads. Those are different claims,
    and the second is the one `validate` makes about a directory.

    **`--install` is how a pack becomes solvable.** A pack-backed library can
    be listed and filtered, and nothing can be attempted from it: the sandbox
    copies a fixture, a stub or a `seed.sql` out of a content *root* by path,
    because a workspace is a real directory (ADR 0021). So the last step is
    always a directory, and `--into` is where it goes.
    """
    if check is not None and install is not None:
        typer.secho(
            "--check and --install are different jobs; run one at a time",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)

    if check is not None:
        _check_pack(check)
        return
    if install is not None:
        _install_pack(install, into)
        return
    _write_pack(
        out if out is not None else Path(f"library{PACK_SUFFIX}"),
        content.resolve() if content is not None else content_root(),
        ExerciseFilter(
            kinds=frozenset(kinds or ()),
            difficulties=frozenset(difficulties or ()),
        ),
    )


def _write_pack(destination: Path, root: Path, criteria: ExerciseFilter) -> None:
    """Export the selection, then read the pack back before calling it good.

    **The read-back is not belt and braces.** Writing an archive is the easy
    half; the claim a pack makes is that somebody else can open it, and the
    cheapest honest way to make that claim is to open it. It also catches the
    one failure the writer cannot see in itself -- a derived `curriculum.yaml`
    or `fixtures.lock` that the parser which produced it would reject.
    """
    selected = FilesystemContentRepository(root).list_exercises(criteria)
    try:
        manifest = write_pack(
            destination.resolve(),
            content_root=root,
            exercises=selected,
            created_with=version("swe-practice"),
        )
    except ContentError as exc:
        typer.secho(f"{_BAD}{exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    try:
        inside = PackContentRepository(destination.resolve()).list_exercises()
    except ContentError as exc:
        typer.secho(
            f"{_BAD}the pack was written and cannot be read back:\n{exc}",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1) from exc

    typer.echo(destination)
    for exercise in inside:
        typer.secho(f"{_OK}{exercise.id}", fg=typer.colors.GREEN)
    typer.echo("")
    typer.echo(
        f"{len(manifest.exercises)} "
        f"{_plural('exercise', len(manifest.exercises))} and "
        f"{len(manifest.digests)} files, "
        f"{_size(destination.resolve().stat().st_size)}."
    )
    typer.echo(f"Install it with `practice pack --install {destination} --into DIR`.")


def _check_pack(archive: Path) -> None:
    """Hash every file against the manifest, then open the library inside it."""
    try:
        problems = verify_pack(archive.resolve())
    except ContentError as exc:
        typer.secho(f"{_BAD}{exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.echo(archive)
    for problem in problems:
        typer.secho(f"{_BAD}{problem}", fg=typer.colors.RED)
    if problems:
        typer.echo("")
        typer.secho(
            "This pack does not match its own manifest. A pack is not signed, "
            "so this says the file was damaged in transit rather than that "
            "nobody edited it -- fetch it again.",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=1)

    repository = PackContentRepository(archive.resolve())
    try:
        inside = repository.list_exercises()
        manifest = repository.manifest()
    except ContentError as exc:
        typer.secho(
            f"{_BAD}every file matches its digest and the library will not "
            f"load:\n{exc}",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1) from exc

    for exercise in inside:
        typer.secho(
            f"{_OK}{exercise.id} ({exercise.kind}, {exercise.difficulty})",
            fg=typer.colors.GREEN,
        )
    typer.echo("")
    written_by = manifest.created_with or "an unrecorded version"
    typer.echo(
        f"{len(inside)} {_plural('exercise', len(inside))}, "
        f"{len(manifest.digests)} files, all matching. Written by {written_by}."
    )


def _install_pack(archive: Path, into: Path | None) -> None:
    """Verify, then lay the pack out as a content root.

    `--into` is required rather than defaulting to the working directory. An
    install writes a tree of several hundred files, and guessing where is the
    one thing it must not do.
    """
    if into is None:
        typer.secho(
            "--install needs --into DIR, the content root to create",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)

    destination = into.resolve()
    if destination.is_dir() and any(destination.iterdir()):
        typer.secho(
            f"{destination} is not empty; installing into it would mix two "
            f"libraries and leave neither valid",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)

    try:
        manifest = install_pack(archive.resolve(), destination)
    except ContentError as exc:
        typer.secho(f"{_BAD}{exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.echo(destination)
    typer.secho(
        f"{_OK}{len(manifest.exercises)} "
        f"{_plural('exercise', len(manifest.exercises))} installed",
        fg=typer.colors.GREEN,
    )
    typer.echo("")
    typer.echo("Check it, and then use it:")
    typer.echo(f"  uv run practice validate --content-root {destination}")
    typer.echo(f"  uv run practice up --content-root {destination}")


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
    db: Annotated[
        Path | None,
        typer.Option(
            "--database",
            envvar=DATABASE_PATH_ENV,
            help="The attempt database. Defaults to the user data directory.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--no-dry-run",
            help="Report only. --no-dry-run deletes the orphans.",
        ),
    ] = True,
) -> None:
    """Report the attempt workspaces left on disk, and collect the orphans.

    An orphan is defined precisely in PLAN.md §8.1: **a workspace directory with
    no corresponding `active` attempt row.** Until Phase 6 there was no attempt
    table, so this command could see the workspaces and not which of them were in
    use, and it refused to delete anything at all — because the alternative was
    collecting the workspace of a session open in another tab.

    **`--dry-run` is still the default**, and that is not timidity. The normal
    state of this command's output is "nothing to collect": an attempt disposes of
    its own workspace when it is submitted, and `practice abandon` does it when
    one is given up on. So an orphan means something went wrong — a process was
    killed, a provision was interrupted — and seeing *what* before deleting it is
    usually worth the second invocation.

    An in-use workspace is never deleted, with or without the flag. There is no
    force option: an active attempt's workspace is not garbage by any definition,
    and the way to get rid of one is `practice abandon`, which says what it means
    and leaves the attempt marked rather than merely workspace-less.
    """
    root = workspaces.resolve() if workspaces is not None else workspace_root()
    services = build_services(
        workspaces=root, database=db.resolve() if db is not None else None
    )
    collected = services.collect_workspaces(delete=not dry_run)

    typer.echo(root)
    if not root.is_dir():
        typer.echo("")
        typer.echo("No workspace directory yet; nothing has been provisioned.")
        return

    for state in collected.workspaces:
        typer.secho(
            f"  {_describe(state)}",
            fg=typer.colors.YELLOW if state.is_orphan else None,
        )

    typer.echo("")
    _report_collection(collected, dry_run=dry_run)


@app.command()
def start(
    exercise: Annotated[
        str,
        typer.Argument(
            help="The exercise id, e.g. git/revert-a-pushed-commit.",
            metavar="EXERCISE_ID",
        ),
    ],
    prompt: Annotated[
        bool,
        typer.Option("--prompt/--no-prompt", help="Print the exercise prompt."),
    ] = True,
    interview: Annotated[
        bool,
        typer.Option(
            "--interview",
            help="Interview conditions: a clock, no hints, no workspace path.",
        ),
    ] = False,
    content: Annotated[
        Path | None,
        typer.Option(
            "--content-root",
            envvar=CONTENT_ROOT_ENV,
            help="The exercise library to start from. Defaults to this project's.",
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
    db: Annotated[
        Path | None,
        typer.Option(
            "--database",
            envvar=DATABASE_PATH_ENV,
            help="The attempt database. Defaults to the user data directory.",
        ),
    ] = None,
) -> None:
    """Open an attempt and leave it open. Prints the id the rest of them take.

    The command that makes the other three worth having, and the one that could
    not exist before this phase: an attempt that outlives the process that
    started it needs somewhere to be written down.

    It provisions the workspace and runs the fixture, so the repository is built
    and waiting by the time this returns — and then stops. Nothing is graded,
    nothing is disposed of, and the attempt stays `ACTIVE` until `submit` or
    `abandon` says otherwise, which is exactly the lifecycle PLAN.md §8.1
    describes.

        practice start git/revert-a-pushed-commit
        practice resume <id> -c my-first-few.cmds
        practice resume <id> -c the-rest.cmds
        practice submit <id>

    That sequence is four processes sharing one repository and one event log,
    which is the thing the attempt table buys. `practice solve` remains the
    one-shot form for a whole answer at once.

    **`--interview` is on this command and not on `solve`, and the asymmetry is
    the point rather than an omission.** Interview mode is about what happens
    *during* an attempt -- a clock running, a hint refused, a path withheld --
    and `solve` has no during: it opens an attempt, grades the answer you had
    already written, and exits. A mode flag there would record a set of rules
    that nothing could have applied (PLAN.md §16).

        practice start katas/two-sum --interview
    """
    library = content.resolve() if content is not None else content_root()
    services = build_services(
        content=library,
        workspaces=workspaces.resolve() if workspaces is not None else None,
        database=db.resolve() if db is not None else None,
    )

    mode = AttemptMode.INTERVIEW if interview else AttemptMode.PRACTICE
    try:
        started = services.start_attempt(_exercise_id(exercise), mode=mode)
    except ApplicationError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    typer.secho(f"{started.exercise.id}  {started.exercise.title}", bold=True)
    if prompt:
        typer.echo("")
        typer.echo(started.exercise.prompt.strip())
    typer.echo("")
    typer.secho(f"{_OK}attempt {started.attempt.id}", fg=typer.colors.GREEN)
    # **No `now` here, deliberately.** The attempt was created a moment ago, so
    # its remaining time is its limit by definition -- and a countdown computed
    # from a clock read microseconds later announces "14 minutes left" of a
    # fifteen minute exercise, which reads as a bug. `resume` passes one,
    # because there the countdown is the whole point.
    typer.echo(_describe_attempt(started.attempt))
    typer.echo("")
    typer.echo(_next_step(started))


@app.command()
def attempts(
    exercise: Annotated[
        str | None,
        typer.Option(
            "--exercise",
            "-e",
            help="Show every attempt at this exercise instead of the open ones.",
            metavar="EXERCISE_ID",
        ),
    ] = None,
    workspaces: Annotated[
        Path | None,
        typer.Option(
            "--workspace-root",
            envvar=WORKSPACE_ROOT_ENV,
            help="Where attempt workspaces live. Defaults to the user cache.",
        ),
    ] = None,
    content: Annotated[
        Path | None,
        typer.Option(
            "--content-root",
            envvar=CONTENT_ROOT_ENV,
            help="The exercise library the attempts refer to.",
        ),
    ] = None,
    db: Annotated[
        Path | None,
        typer.Option(
            "--database",
            envvar=DATABASE_PATH_ENV,
            help="The attempt database. Defaults to the user data directory.",
        ),
    ] = None,
) -> None:
    """List the attempts that are still open, oldest first.

    This is the resume-or-abandon prompt of PLAN.md §8.1, in the form a terminal
    can have one. An interactive question on startup would be the literal reading
    and the wrong one here: it would block `practice solve` in CI and make every
    command unusable from a script. A list plus `resume` and `abandon` is the same
    guarantee — an interrupted session is neither silently lost nor silently
    resurrected — without a command that waits for a human.

    Each line says whether the attempt **can** be resumed. One whose workspace has
    been collected cannot, and the only thing left to do with it is abandon it; the
    listing says so rather than letting `resume` be the thing that finds out.

    With `--exercise` it shows that exercise's whole history instead, finished
    attempts included, which is the other question the attempt table can now
    answer.
    """
    services = build_services(
        content=content.resolve() if content is not None else None,
        workspaces=workspaces.resolve() if workspaces is not None else None,
        database=db.resolve() if db is not None else None,
    )

    if exercise is not None:
        _report_history(services, _exercise_id(exercise))
        return

    open_attempts = services.list_open_attempts()
    if not open_attempts:
        typer.echo("No open attempts.")
        return

    for found in open_attempts:
        _report_open_attempt(found)
    typer.echo("")
    typer.echo(
        f"{len(open_attempts)} open {_plural('attempt', len(open_attempts))}. "
        f"Resume one with `practice resume <id>`, or `practice abandon <id>`."
    )


@app.command()
def resume(
    attempt: Annotated[
        str,
        typer.Argument(help="The attempt id, as `practice attempts` prints it."),
    ],
    commands: Annotated[
        Path | None,
        typer.Option(
            "--commands",
            "-c",
            help="Git scenario: more commands to run, one per line.",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    content: Annotated[
        Path | None,
        typer.Option(
            "--content-root",
            envvar=CONTENT_ROOT_ENV,
            help="The exercise library the attempt refers to.",
        ),
    ] = None,
    workspaces: Annotated[
        Path | None,
        typer.Option(
            "--workspace-root",
            envvar=WORKSPACE_ROOT_ENV,
            help="Where attempt workspaces live. Defaults to the user cache.",
        ),
    ] = None,
    db: Annotated[
        Path | None,
        typer.Option(
            "--database",
            envvar=DATABASE_PATH_ENV,
            help="The attempt database. Defaults to the user data directory.",
        ),
    ] = None,
) -> None:
    """Pick up an attempt a previous process started, and optionally carry on.

    With no `--commands` it reports where the attempt stands: what it has run, what
    budget is left, and what to do next. That is the useful half for a kata, where
    there is nothing to replay — the next step is `practice submit --source`.

    With `--commands` it replays more commands into the same repository, through
    the same policy and against the same budget. The budget is the attempt's, not
    the invocation's, which is the thing that makes this a resumption rather than a
    second attempt: ten commands yesterday and five today is fifteen of twenty-five.

    Nothing is written by resuming itself. The attempt stays active and its log is
    untouched until a command actually runs, because reopening a session is not
    something the solver did and the advisory checks in PLAN.md §6.3 read that log.
    """
    services = build_services(
        content=content.resolve() if content is not None else None,
        workspaces=workspaces.resolve() if workspaces is not None else None,
        database=db.resolve() if db is not None else None,
    )
    resumed = _load(services.resume_attempt, attempt)

    typer.secho(f"{resumed.exercise.id}  {resumed.exercise.title}", bold=True)
    typer.echo(_describe_attempt(resumed.attempt, now=services.clock.now()))

    if commands is None:
        typer.echo("")
        typer.echo(_next_step(resumed))
        return

    if not isinstance(resumed.exercise.spec, GitScenarioSpec):
        typer.secho(
            f"{resumed.exercise.id} is a {resumed.exercise.kind.value} and has no "
            f"command console; submit a solution with "
            f"`practice submit {resumed.attempt.id} --source FILE`.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)

    typer.echo("")
    _replay(services, resumed.attempt.id, commands.read_text(encoding="utf-8"))
    typer.echo("")
    typer.echo(f"Not submitted. Grade it with `practice submit {resumed.attempt.id}`.")


@app.command()
def submit(
    attempt: Annotated[
        str,
        typer.Argument(help="The attempt id, as `practice attempts` prints it."),
    ],
    source: Annotated[
        Path | None,
        typer.Option(
            "--source",
            "-s",
            help="Kata: the file holding your solution.",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    time: Annotated[
        str | None,
        typer.Option("--time", help="Your claimed time complexity, e.g. O(n)."),
    ] = None,
    space: Annotated[
        str | None,
        typer.Option("--space", help="Your claimed space complexity, e.g. O(n)."),
    ] = None,
    content: Annotated[
        Path | None,
        typer.Option(
            "--content-root",
            envvar=CONTENT_ROOT_ENV,
            help="The exercise library the attempt refers to.",
        ),
    ] = None,
    workspaces: Annotated[
        Path | None,
        typer.Option(
            "--workspace-root",
            envvar=WORKSPACE_ROOT_ENV,
            help="Where attempt workspaces live. Defaults to the user cache.",
        ),
    ] = None,
    db: Annotated[
        Path | None,
        typer.Option(
            "--database",
            envvar=DATABASE_PATH_ENV,
            help="The attempt database. Defaults to the user data directory.",
        ),
    ] = None,
) -> None:
    """Grade an attempt that is already open, and close it.

    The other end of `resume`, and the same exit codes as `solve`: 0 on a pass
    including a pass with advisories, 1 when a required check fails, 2 when the
    attempt could not be graded at all.

    A **git scenario** takes nothing — the repository is already on disk and the
    log already holds every command that put it there. A **kata** takes `--source`,
    because a kata's answer is not in the workspace until it is submitted.

    The workspace is disposed of on success and kept on failure, which is PLAN.md
    §8.1's rule rather than this command's: the attempt is still active if grading
    could not happen, and the repository is the only thing that could explain why.
    """
    services = build_services(
        content=content.resolve() if content is not None else None,
        workspaces=workspaces.resolve() if workspaces is not None else None,
        database=db.resolve() if db is not None else None,
    )
    resumed = _load(services.resume_attempt, attempt)
    claim = _claim(time, space)
    scenario = isinstance(resumed.exercise.spec, GitScenarioSpec)

    if scenario and (source is not None or claim is not None):
        typer.secho(
            f"{resumed.exercise.id} is a git scenario: it is graded on the "
            f"repository as you left it, so it takes neither --source nor "
            f"--time/--space.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)
    if not scenario and source is None:
        typer.secho(
            f"{resumed.exercise.id} is a {resumed.exercise.kind.value}: pass "
            f"--source FILE with the solution to grade.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=2)

    typer.secho(f"{resumed.exercise.id}  {resumed.exercise.title}", bold=True)
    typer.echo("")

    try:
        if scenario:
            submission = services.submit_scenario(resumed.attempt.id)
            origin = "the repository as you left it"
        else:
            assert source is not None  # noqa: S101  (refused above; narrowing only)
            submission = services.submit_solution(
                resumed.attempt.id,
                source.read_text(encoding="utf-8"),
                complexity=claim,
            )
            origin = str(source)
    except (ApplicationError, DomainError, OSError) as exc:
        typer.secho(f"cannot grade this attempt: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    typer.echo(f"graded {origin}")
    typer.echo("")
    _report_verdict(submission)

    if not submission.passed:
        raise typer.Exit(code=1)


@app.command()
def abandon(
    attempt: Annotated[
        str,
        typer.Argument(help="The attempt id, as `practice attempts` prints it."),
    ],
    content: Annotated[
        Path | None,
        typer.Option(
            "--content-root",
            envvar=CONTENT_ROOT_ENV,
            help="The exercise library the attempt refers to.",
        ),
    ] = None,
    workspaces: Annotated[
        Path | None,
        typer.Option(
            "--workspace-root",
            envvar=WORKSPACE_ROOT_ENV,
            help="Where attempt workspaces live. Defaults to the user cache.",
        ),
    ] = None,
    db: Annotated[
        Path | None,
        typer.Option(
            "--database",
            envvar=DATABASE_PATH_ENV,
            help="The attempt database. Defaults to the user data directory.",
        ),
    ] = None,
) -> None:
    """Give up on an attempt, and delete the workspace it was using.

    The explicit *no* that PLAN.md §8.1's resume-or-abandon promise needs. The
    attempt row stays, marked `abandoned`, with its whole event log: the history is
    the point, and an attempt someone walked away from is as much of a fact as one
    they finished.

    This is also the way out of the one state nothing else can fix — an exercise
    renamed or deleted from the library under a live attempt. That attempt can
    never be graded, so `resume` refuses it; this does not, because it does not
    need the exercise to collect the directory.
    """
    services = build_services(
        content=content.resolve() if content is not None else None,
        workspaces=workspaces.resolve() if workspaces is not None else None,
        database=db.resolve() if db is not None else None,
    )

    try:
        abandoned = services.abandon_attempt(_attempt_id(attempt))
    except (ApplicationError, DomainError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc

    label = (
        str(abandoned.attempt.exercise_id)
        if abandoned.exercise is None
        else f"{abandoned.exercise.id}  {abandoned.exercise.title}"
    )
    typer.secho(f"{_OK}abandoned {abandoned.attempt.id.short}  {label}")
    typer.echo(f"{_INDENT}{_describe_attempt(abandoned.attempt).strip()}")
    typer.echo(f"{_INDENT}workspace deleted; the attempt is kept in your history.")


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
    db: Annotated[
        Path | None,
        typer.Option(
            "--database",
            envvar=DATABASE_PATH_ENV,
            help="The attempt database. Defaults to the user data directory.",
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
        database=db.resolve() if db is not None else None,
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


@app.command()
def serve(
    host: Annotated[
        str,
        typer.Option(
            "--host",
            help="Must be a loopback address. Anything else is refused.",
        ),
    ] = DEFAULT_HOST,
    port: Annotated[
        int,
        typer.Option("--port", help="The port to listen on."),
    ] = DEFAULT_PORT,
    content: Annotated[
        Path | None,
        typer.Option(
            "--content-root",
            envvar=CONTENT_ROOT_ENV,
            help="The exercise library to serve. Defaults to this project's.",
        ),
    ] = None,
    workspaces: Annotated[
        Path | None,
        typer.Option(
            "--workspace-root",
            envvar=WORKSPACE_ROOT_ENV,
            help="Where attempts are provisioned. Defaults to the user cache.",
        ),
    ] = None,
    db: Annotated[
        Path | None,
        typer.Option(
            "--database",
            envvar=DATABASE_PATH_ENV,
            help="The attempt database. Defaults to the user data directory.",
        ),
    ] = None,
) -> None:
    """Run the web app on loopback, and nothing else.

    **This command is not in PLAN.md §11's list for phase 7, and the phase does
    not work without it** -- the same omission §16 records for `practice start` in
    phase 6, and the same shape: the exit criterion is *a kata solved entirely in
    the browser*, and nothing in the shipped CLI could open a browser at. A
    commit list can be in dependency order and still describe a product with no
    way into the state it adds.

    The host is checked by `require_loopback` rather than by this function, and
    the check is in the *argument* to `uvicorn.run`: a guard on the line above
    is a guard someone deletes while rebasing. A server listening on `0.0.0.0`
    has published a code-execution endpoint to the network before the first
    request arrives, which is why this refuses rather than warning (PLAN.md §8.3).

    `--reload` is deliberately absent. It makes uvicorn import the app by string
    in a child process, which means the app would have to build its own services
    from a global -- and `create_app` taking the object graph is the thing that
    keeps the web adapter from becoming a second wiring point.
    """
    bind = _bound(host)
    services = build_services(
        content=content.resolve() if content is not None else None,
        workspaces=workspaces.resolve() if workspaces is not None else None,
        database=db.resolve() if db is not None else None,
    )

    typer.echo(f"http://{bind}:{port}")
    typer.echo("")
    typer.echo("Offline: every asset is served from disk, and nothing is fetched.")
    _listen(services, bind, port)


def _bound(host: str) -> str:
    """The address to bind, or exit 2 saying why this one will not be bound.

    Shared by `serve` and `up` so that §8.3's first guard has one
    implementation and one test. A second command with its own copy of this
    check is a second command somebody can forget to update.
    """
    try:
        return require_loopback(host)
    except NotLoopbackError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc


def _listen(services: Services, bind: str, port: int) -> None:
    """Hand the built app to uvicorn and block until Ctrl-C.

    One call site for `uvicorn.run`, which is also what lets
    `tests/web/test_serve.py` substitute it once and cover both commands.
    """
    typer.echo("Stop it with Ctrl-C.")
    uvicorn.run(create_app(services), host=bind, port=port, log_level="warning")


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
            f"solution. For an interactive console, run `practice serve`.",
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

    _replay(services, started.attempt.id, text)

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


def _replay(services: Services, attempt_id: AttemptId, text: str) -> None:
    """Run a `.cmds` file against an attempt, echoing a transcript as it goes.

    Shared by `solve` and `resume`, which is the point: a resumed attempt's
    commands go through the same use case, the same policy and the same budget as
    a fresh one's. If the two had their own loops, "resuming is the same as
    carrying on" would be a claim about two pieces of code that happen to agree.
    """
    run = services.run_scenario_command
    for command in parse_command_list(text):
        result = run(attempt_id, command.text).command.result
        typer.secho(
            f"{_command_marker(result)}$ {command.text}",
            fg=_command_colour(result),
        )
        for line in _transcript(result):
            typer.echo(f"{_INDENT}{line}")


def _attempt_id(value: str) -> AttemptId:
    """Parse an attempt id, refusing anything that is not one.

    A separate message from "no attempt with that id", because the two have
    different fixes: a malformed id is usually a truncated paste, and being told
    the attempt does not exist would send someone looking for the wrong problem.
    """
    try:
        return AttemptId.parse(value)
    except InvalidValueError as exc:
        typer.secho(
            f"{exc}. `practice attempts` prints ids in full.", fg=typer.colors.RED
        )
        raise typer.Exit(code=2) from exc


def _exercise_id(value: str) -> ExerciseId:
    try:
        return ExerciseId(value)
    except InvalidValueError as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc


def _load(resume_attempt: ResumeAttempt, value: str) -> StartedAttempt:
    """Find an open attempt and reattach its workspace, or exit with the reason.

    `resume`, `submit` and nothing else: both commands need the attempt, its
    exercise and the knowledge that its workspace is still there before they can
    say anything, and `ResumeAttempt` is the use case that establishes all three.
    """
    try:
        return resume_attempt(_attempt_id(value))
    except (ApplicationError, DomainError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=2) from exc


def _describe_attempt(attempt: Attempt, *, now: datetime | None = None) -> str:
    """One line of state: when it started, what it has used, what is left.

    **An interview reads differently in two places, and both are the same
    decision: say what the rules are rather than printing a field that is
    technically true.** "0 of 0 hints" is true of every interview attempt and
    tells the solver nothing, so the clause becomes `no hints`; and the clock is
    the fact that matters, so it replaces the count that is now constant.

    `now` is optional because one caller has no clock to offer -- `practice
    attempts` lists rows it has not provisioned services for -- and the honest
    thing to print without one is the budget rather than a countdown computed
    from a time this function invented.
    """
    used = (
        f"{attempt.command_count}/{attempt.policy.max_commands} commands"
        if attempt.policy.max_commands
        else f"{len(attempt.events)} {_plural('event', len(attempt.events))}"
    )
    hints = (
        ", no hints"
        if attempt.policy.is_interview
        else f", {attempt.hints_revealed} of {attempt.policy.hint_count} hints"
    )
    return (
        f"{_INDENT}started {attempt.started_at.isoformat(timespec='seconds')}, "
        f"{used}{hints}{_clock(attempt, now)}"
    )


def _clock(attempt: Attempt, now: datetime | None) -> str:
    """The interview clock, as a clause to append. Empty for a practice run.

    Whole minutes, which is the unit the deadline is authored in. Seconds would
    be a precision the estimate does not have and a figure that is wrong by the
    time it is read.

    **The two directions round opposite ways, and each lean is the safe one.**
    Time left rounds *up*, because a clock face does: fourteen minutes and
    fifty-nine seconds reads as fifteen, and flooring it would announce "0
    minutes left" to somebody with the better part of a minute in hand — which
    is the one reading that would make the solver stop early for no reason.
    Overrun rounds *down*, so being two and a half minutes late is never
    reported as three.

    `now` is optional because `practice attempts` has no clock to offer, and the
    honest thing to print without one is the limit rather than a countdown from
    a time this function invented.
    """
    seconds = attempt.policy.deadline_seconds
    if seconds is None:
        return ""
    if now is None:
        return f", {seconds // 60} minute limit"
    left = attempt.remaining(now)
    assert left is not None  # noqa: S101  (a deadline implies a remainder)
    if left.total_seconds() < 0:
        return f", {_minutes(-left.total_seconds() // 60)} over"
    return f", {_minutes(-(-left.total_seconds() // 60))} left"


def _minutes(whole: float) -> str:
    return f"{int(whole)} {_plural('minute', int(whole))}"


def _report_open_attempt(found: OpenAttempt) -> None:
    """One open attempt, and whether it can be resumed at all.

    The id in full, because that is what `resume` takes; the short form is the
    workspace directory's name and nothing accepts it (PLAN.md §8.1).
    """
    marker = _OK if found.can_resume else _NOTE
    colour = typer.colors.GREEN if found.can_resume else typer.colors.YELLOW
    typer.secho(f"{marker}{found.attempt.id}  {found.label}", fg=colour)
    typer.echo(_describe_attempt(found.attempt))
    if found.exercise is None:
        typer.echo(f"{_INDENT}the exercise is gone, so this can only be abandoned")
    elif not found.workspace_on_disk:
        typer.echo(
            f"{_INDENT}the workspace has been collected, so this can only be abandoned"
        )


def _report_history(services: Services, exercise_id: ExerciseId) -> None:
    """Every attempt at one exercise, finished ones included.

    The other question the attempt table can now answer, and the reason the
    `history_for` port method has had no caller until this phase.

    **This reads the repository port directly rather than through a use case, and
    that is the deliberate choice rather than a shortcut.** Every other command
    here goes through one because a use case adds something: a join the caller
    would otherwise make itself, an ordering of operations, a refusal. There is
    nothing to add here — the exercise is the argument, so there is no join, and a
    listing has no ordering to get wrong. A `ListAttemptHistory` that forwarded one
    call and returned its result unchanged is the abstraction PLAN.md §13 says to
    delete rather than write. It gains one the moment this needs anything the
    repository does not already answer.
    """
    history = services.attempts.history_for(exercise_id)
    if not history:
        typer.echo(f"No attempts at {exercise_id}.")
        return

    for attempt in history:
        outcome = (
            _OUTCOMES[attempt.verdict.outcome]
            if attempt.verdict is not None
            else attempt.status.value
        )
        typer.echo(f"  {attempt.id}  {outcome}")
        typer.echo(_describe_attempt(attempt))
    typer.echo("")
    typer.echo(f"{len(history)} {_plural('attempt', len(history))} at {exercise_id}.")


def _next_step(resumed: StartedAttempt) -> str:
    """What to type next, which depends only on the exercise kind.

    **A kata names its file rather than saying `FILE`**, which is the CLI's half
    of the own-editor mode Phase 10 adds: the stub has been copied into the
    workspace since Phase 3, so the loop *already worked* — edit the file, then
    `submit --source` it — and the only thing missing was ever its path. That is
    the finding the phase opened with, and it cost one line here (PLAN.md §16).

    A SQL drill takes the same branch unchanged, which is the dividend of
    `editable_source` existing: the sentence was never about katas, it was about
    exercises you solve by editing a file.

    Printed on two lines because a Windows workspace path plus a uuid plus
    `--source` is well past 80 characters, and a wrapped instruction is an
    instruction somebody mistypes.

    **Under interview mode the path is not printed**, which is the CLI half of
    Phase 15's third clause and the reason it is a sentence here rather than a
    deletion. The workspace holds a kata's `tests.py`, and naming the directory
    is the tool offering to show it. Withdrawing the offer leaves `--source`
    still working on a file the solver wrote themselves, which is what an
    interview actually looks like -- so the instruction changes rather than
    disappearing. It is not containment, and
    `AttemptPolicy.reveals_workspace` says why at length.
    """
    if isinstance(resumed.exercise.spec, GitScenarioSpec):
        return (
            f"Run more commands with `practice resume {resumed.attempt.id} "
            f"-c FILE`, or grade it with `practice submit {resumed.attempt.id}`."
        )
    if not resumed.attempt.policy.reveals_workspace:
        return (
            f"Write your answer in a file of your own, then grade it with\n"
            f"`practice submit {resumed.attempt.id} --source FILE`."
        )
    solution = _solution_path(resumed)
    return (
        f"Edit {solution} in your own editor, then grade it with\n"
        f"`practice submit {resumed.attempt.id} --source {solution}`."
    )


def _solution_path(resumed: StartedAttempt) -> Path:
    """Where this attempt's editable source lives on disk.

    Through `Workspace.resolve` rather than by joining paths here: the interface
    layer has no business knowing that a workspace keeps its repository in a
    subdirectory, and the port exists to answer exactly this.
    """
    source = editable_source(resumed.exercise.spec)
    assert source is not None  # noqa: S101  (checked by the caller)
    return resumed.workspace.resolve(source.filename)


def _describe(state: WorkspaceState) -> str:
    """One workspace, on one line, with the orphan rule's answer on it.

    An undescribed workspace is called out rather than skipped: it means a
    provision was interrupted before it wrote its metadata, which is precisely
    the kind of leftover worth knowing about — and, now that the rule is decided
    on the directory name, one that gc can still collect.
    """
    found = state.workspace
    owner = "in use" if state.in_use else "orphan"
    if not found.is_described:
        return (
            f"{found.short_id}  (no readable metadata: an interrupted "
            f"provision)  {_size(found.size_bytes)}  {owner}"
        )
    return (
        f"{found.short_id}  {found.exercise_id}  "
        f"{found.created_at}  {_size(found.size_bytes)}  {owner}"
    )


def _report_collection(collected: Collection, *, dry_run: bool) -> None:
    """The summary line, and what to do about it.

    Says what was *not* collected as well as what was, because "2 workspaces, 1
    collected" without the reason reads like a failure rather than the rule
    working.
    """
    total = len(collected.workspaces)
    if not total:
        typer.echo("No workspaces.")
        return

    typer.echo(
        f"{total} {_plural('workspace', total)}, {_size(collected.total_bytes)}: "
        f"{len(collected.in_use)} in use, {len(collected.orphans)} "
        f"{_plural('orphan', len(collected.orphans))}."
    )
    if collected.deleted:
        typer.secho(
            f"{_OK}collected {len(collected.deleted)} "
            f"{_plural('workspace', len(collected.deleted))}, freeing "
            f"{_size(collected.reclaimable_bytes)}.",
            fg=typer.colors.GREEN,
        )
    elif collected.orphans and dry_run:
        typer.secho(
            f"Nothing deleted. {_size(collected.reclaimable_bytes)} is "
            f"collectable; re-run with --no-dry-run to free it.",
            fg=typer.colors.YELLOW,
        )
    elif collected.in_use:
        typer.echo(
            "Nothing to collect: every workspace here belongs to an attempt that "
            "is still open. Abandon one with `practice abandon <id>`."
        )


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

    editable = editable_source(started.exercise.spec)
    if editable is None:  # pragma: no cover - the registry refuses first
        message = f"{started.exercise.id} has no stub to fall back to"
        raise ApplicationError(message)

    name = editable.reference if reference else editable.filename
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


def _summarise(total: int, failed: int, problems: int) -> str:
    """The last line `validate` prints, which has to agree with the ones above it.

    `problems` is the library-level count — a curriculum that does not list an
    exercise, a duplicate id, a missing manifest — and it is a separate argument
    because it is a separate claim: every exercise can be individually valid in
    a library that is not. Without it this said "62 exercises, all valid."
    directly underneath its own `FAIL` line, which is the one sentence a reader
    takes away from the command.
    """
    exercises = _plural("exercise", total)
    if not total:
        return "No exercises found."
    if failed:
        verb = "has" if failed == 1 else "have"
        body = f"{failed} of {total} {exercises} {verb} problems"
    elif problems:
        body = f"{total} {exercises}, each valid on its own"
    else:
        return f"{total} {exercises}, all valid."
    if not problems:
        return f"{body}."
    return f"{body}, and {problems} {_plural('problem', problems)} with the library."
