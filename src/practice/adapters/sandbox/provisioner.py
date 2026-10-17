"""Building a workspace for an attempt, and finding the ones already built.

Satisfies `practice.domain.ports.SandboxProvisioner`, with one deviation from
the sketch in PLAN.md §4.6 recorded in §16: `provision` takes the `AttemptId` as
well as the `Exercise`. The workspace directory is named after the attempt
(§8.1), so the alternative is for the provisioner to generate identity — which
would mean the `Attempt` aggregate learns its own id from its workspace, and the
`IdGenerator` port is injected in two places to produce one id.

**The pinned git config is the reproducibility guarantee, written down.** Every
setting in `_GITCONFIG` is there because leaving it to a default makes commit
hashes depend on the machine, or makes an exercise behave differently from the
one the author tested. The table in PLAN.md §6.1 explains the first four; the
rest earned their place while building this:

* `gc.auto=0` and the two reflog expiry settings. `content/git/
  recover-a-lost-commit` works by recovering commits that no ref points at. A
  garbage collection — which git will start on its own, in the background, after
  enough loose objects accumulate — is entitled to delete exactly those, and the
  exercise would then be unsolvable for reasons nobody could reproduce.
* `color.ui=false`. Output is captured through a pipe, so git disables colour
  anyway; pinning it means a future change that renders in a terminal cannot
  start smuggling ANSI escapes into graded output.
* `core.symlinks=false`. A symlink commits as mode `120000` where it is
  supported and as a regular file where it is not, which is the `core.fileMode`
  problem again in a form the §6.1 table does not cover. Fixtures do not create
  symlinks; this makes the consequence of one a checkout difference rather than
  a silent hash divergence.

Note what is deliberately *not* pinned: `advice.detachedHead`. That advice is
the lesson in at least one exercise, and turning it off to reduce noise would be
turning off the teaching.
"""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final

from practice.adapters.sandbox.command_policy import CommandPolicy
from practice.adapters.sandbox.env import (
    FIXTURE_IDENTITY,
    SandboxClock,
    sandbox_environment,
    sandbox_path_entries,
)
from practice.adapters.sandbox.fixture_runner import run_fixture
from practice.adapters.sandbox.workspace import (
    SubprocessWorkspace,
    WorkspaceLayout,
    WorkspacePathError,
)
from practice.domain.exercise import (
    ContainerSpec,
    GitScenarioSpec,
    KataSpec,
    SqlDrillSpec,
)
from practice.domain.ids import AttemptId, ExerciseId
from practice.domain.ports import WorkspaceSummary

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from practice.domain.exercise import Exercise
    from practice.domain.ports import Clock

__all__ = [
    "FIXTURE_LIB_PATH",
    "SubprocessSandboxProvisioner",
    "WorkspaceExistsError",
]

#: The shared fixture helpers, relative to the content root.
FIXTURE_LIB_PATH: Final = Path("_lib") / "fixture_lib.sh"

#: Written to `<workspace>/.gitconfig`, which is both `GIT_CONFIG_GLOBAL` and
#: `~/.gitconfig` since `HOME` points at the workspace. Set explicitly on both
#: platforms rather than left to defaults, because a reproducibility guarantee
#: must not rest on a default an installer can change (PLAN.md §6.1).
_GITCONFIG: Final = """\
# Written by the provisioner. Every setting here is pinned because a default
# would make commit hashes depend on the machine -- see PLAN.md 6.1 and
# adapters/sandbox/provisioner.py for why each one is needed.
[core]
\tfileMode = false
\tautocrlf = false
\teol = lf
\tlongpaths = true
\tsymlinks = false
\tpager = cat
[init]
\tdefaultBranch = main
[user]
\tname = {name}
\temail = {email}
[commit]
\tgpgSign = false
[tag]
\tgpgSign = false
[color]
\tui = false
[push]
\tdefault = simple
[pull]
\trebase = false
[gc]
\tauto = 0
\treflogExpire = never
\treflogExpireUnreachable = never
"""


class WorkspaceExistsError(Exception):
    """A workspace for this attempt is already on disk.

    Refused rather than overwritten, because the only two things it can mean are
    both bad to guess at: an attempt is open in another tab, or a previous
    process died and its work is still there. `attach` resumes it; `dispose`
    throws it away. Silently clobbering it would make the resume-or-abandon
    promise in PLAN.md §8.1 a lie.
    """


class SubprocessSandboxProvisioner:
    """Provisions workspaces under one root, from one content library.

    Satisfies the `SandboxProvisioner` port structurally; it does not import it
    (ADR 0002).
    """

    __slots__ = ("_clock", "_content_root", "_identity", "_root")

    def __init__(
        self,
        *,
        content_root: Path,
        workspace_root: Path,
        clock: Clock | None = None,
    ) -> None:
        self._content_root = content_root
        self._root = workspace_root
        self._clock = clock
        self._identity = FIXTURE_IDENTITY

    @property
    def root(self) -> Path:
        return self._root

    # --- provisioning -------------------------------------------------------

    def provision(
        self, exercise: Exercise, attempt_id: AttemptId
    ) -> SubprocessWorkspace:
        """Build a workspace for this attempt and run the exercise's fixture.

        A kata gets the same scoped workspace with its files copied in and no
        repository: the Phase 4 runner needs somewhere isolated to run pytest,
        and that is the same somewhere. Treating it as a kind of workspace
        rather than a special case is what stops the kata engine growing its own
        parallel notion of one.

        **A SQL drill is the cheapest of the three and the one that proves the
        claim.** It needs two files copied and nothing else -- no fixture, no
        git, no database. The drill engine builds its database in memory from
        `seed.sql` on every grading pass (`adapters/sql/engine.py`), so there is
        nothing here to create and nothing to keep in step: this method gained
        four lines and the dispatch stopped being an `else`.

        The `else` is worth noting as the one thing a third kind broke here.
        `if scenario ... else kata` had been quietly asserting that
        not-a-scenario means a kata, and widening the spec union turned that into
        the single `mypy` error this phase's first commit produced -- which is
        the architecture test working in the form that costs nothing to run.
        """
        layout = self.layout_for(attempt_id)
        if layout.exists:
            raise WorkspaceExistsError(
                f"a workspace for attempt {attempt_id.short} already exists at "
                f"{layout.root}; resume it with attach(), or dispose of it first"
            )

        layout.create()
        self._write_gitconfig(layout)
        self._write_metadata(layout, exercise=exercise, attempt_id=attempt_id)
        SandboxClock(layout.clock).start()
        layout.aliases.write_text("", encoding="utf-8")
        layout.snapshot.write_text("", encoding="utf-8")

        directory = self.directory_for(exercise.id)
        spec = exercise.spec
        if isinstance(spec, GitScenarioSpec):
            self._install_fixture(layout, directory=directory, spec=spec)
            run_fixture(layout, environment=self._environment(layout))
        elif isinstance(spec, KataSpec):
            self._install_kata_files(layout, directory=directory, spec=spec)
        elif isinstance(spec, SqlDrillSpec):
            self._install_drill_files(layout, directory=directory, spec=spec)
        else:
            self._install_container_files(layout, directory=directory, spec=spec)

        return self._workspace(layout, policy=CommandPolicy.for_exercise(exercise))

    def attach(
        self, exercise: Exercise, attempt_id: AttemptId
    ) -> SubprocessWorkspace | None:
        """Reopen an existing workspace without touching what is in it.

        The resume half of PLAN.md §8.1. `None` rather than an exception when
        there is nothing there: an attempt whose workspace has been collected is
        a normal thing for the caller to decide about, not a fault.
        """
        layout = self.layout_for(attempt_id)
        if not layout.exists:
            return None
        return self._workspace(layout, policy=CommandPolicy.for_exercise(exercise))

    # --- reading what is on disk -------------------------------------------

    def layout_for(self, attempt_id: AttemptId) -> WorkspaceLayout:
        """Where this attempt's workspace goes. Does not create anything."""
        return WorkspaceLayout(self._root / attempt_id.short)

    def directory_for(self, exercise_id: ExerciseId) -> Path:
        """The exercise's content directory.

        Derived from the id rather than carried on the `Exercise`, because the
        domain holds no filesystem paths — and the id *is* the content path
        (PLAN.md §4.1), an invariant the content suite asserts per exercise.
        """
        return self._content_root / exercise_id.value

    def workspaces(self) -> Sequence[WorkspaceSummary]:
        """Every workspace under the root, in a stable order.

        What `practice gc` enumerates. Reports rather than filters: deciding which
        of these is an orphan is a question about the attempt table, and this class
        has never heard of it — `CollectWorkspaces` joins the two.
        """
        if not self._root.is_dir():
            return ()
        return tuple(
            self._summarise(WorkspaceLayout(directory))
            for directory in sorted(self._root.iterdir())
            if directory.is_dir()
        )

    def discard(self, short_id: str) -> None:
        """Delete one workspace by its directory name. Safe to call twice.

        The name is checked against the root rather than trusted, even though it
        comes from a listing this class itself produced. One `..` in it and this
        becomes a recursive delete of something else, which is too large a
        consequence to leave resting on where the string came from — and the check
        costs one comparison.
        """
        candidate = Path(short_id)
        if candidate.name != short_id or short_id in {"", ".", ".."}:
            raise WorkspacePathError(
                f"{short_id!r} is not a workspace directory name; "
                f"gc works on the names `workspaces()` reports"
            )
        WorkspaceLayout(self._root / short_id).destroy()

    # --- the pieces --------------------------------------------------------

    def _workspace(
        self, layout: WorkspaceLayout, *, policy: CommandPolicy
    ) -> SubprocessWorkspace:
        return SubprocessWorkspace(
            layout,
            policy=policy,
            environment=self._environment(layout),
        )

    def _environment(self, layout: WorkspaceLayout) -> Mapping[str, str]:
        return sandbox_environment(
            layout.paths(),
            path_entries=sandbox_path_entries(),
            identity=self._identity,
        )

    def _write_gitconfig(self, layout: WorkspaceLayout) -> None:
        layout.gitconfig.write_text(
            _GITCONFIG.format(name=self._identity.name, email=self._identity.email),
            encoding="utf-8",
            newline="",
        )

    def _write_metadata(
        self, layout: WorkspaceLayout, *, exercise: Exercise, attempt_id: AttemptId
    ) -> None:
        layout.metadata.write_text(
            json.dumps(
                {
                    "attempt_id": str(attempt_id),
                    "exercise_id": str(exercise.id),
                    "created_at": self._now(),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
            newline="",
        )

    def _now(self) -> str:
        """An ISO timestamp for the metadata.

        Through the `Clock` port when one is injected, so a test can produce a
        stable workspace record; through the system clock otherwise, because
        `practice fixtures` builds throwaway workspaces and should not have to
        wire a clock to do it.
        """
        now = self._clock.now() if self._clock is not None else datetime.now(UTC)
        return now.isoformat()

    def _install_fixture(
        self, layout: WorkspaceLayout, *, directory: Path, spec: GitScenarioSpec
    ) -> None:
        """Copy the fixture and the shared helper library into the workspace.

        Copied rather than run from the content directory, so a fixture cannot
        reach its own siblings — `solution.cmds` and the counter-examples are
        the answers, and they are not in the workspace at all.
        """
        shutil.copyfile(self._content_root / FIXTURE_LIB_PATH, layout.fixture_lib)
        shutil.copyfile(directory / spec.fixture, layout.fixture)

    def _install_kata_files(
        self, layout: WorkspaceLayout, *, directory: Path, spec: KataSpec
    ) -> None:
        """Copy the stub and the tests in. The reference is left behind.

        Deliberate: the workspace is where the solver's code runs, and a
        reference solution sitting next to it is an answer key inside the exam.
        Phase 4 copies it in separately, for the content test that proves the
        reference passes.
        """
        for name in (spec.stub, spec.tests):
            shutil.copyfile(directory / name, layout.repo / name)

    def _install_container_files(
        self, layout: WorkspaceLayout, *, directory: Path, spec: ContainerSpec
    ) -> None:
        """Copy the build context in whole, then the editable file beside it.

        The workspace *is* the build context, so `docker build .` and `docker
        compose up` work in it unchanged and the solver can watch the symptom
        happen. The reference and counter-examples stay in the content
        directory, the answer key staying outside the exam as it does for
        every kind.
        """
        shutil.copytree(directory / spec.context, layout.repo, dirs_exist_ok=True)
        shutil.copyfile(directory / spec.stub, layout.repo / spec.stub)

    def _install_drill_files(
        self, layout: WorkspaceLayout, *, directory: Path, spec: SqlDrillSpec
    ) -> None:
        """Copy the seed and the stub in. The reference is left behind.

        The same split as a kata's, with one deliberate difference in what the
        solver can see. A kata's `tests.py` is copied in because pytest has to
        run it, and a solver reading it is an accepted cost. A drill's
        `seed.sql` is copied in because the grader reads it from the workspace
        *and* because the solver is meant to read it: the schema is not the
        answer, it is the question, and a drill with a hidden schema would be a
        riddle rather than an exercise.

        `solution.sql` and the counter-examples stay in the content directory,
        which is the answer key staying outside the exam.
        """
        for name in (spec.seed, spec.stub):
            shutil.copyfile(directory / name, layout.repo / name)

    def _summarise(self, layout: WorkspaceLayout) -> WorkspaceSummary:
        """Read a workspace's metadata, tolerating every way it can be absent.

        Unreadable metadata produces a summary with empty fields rather than an
        error. gc has to be able to describe a workspace whose provisioning was
        interrupted — that is one of the things it exists to find, and the
        `short_id` it is collected by comes from the directory name either way.
        """
        attempt_id: AttemptId | None = None
        exercise_id: ExerciseId | None = None
        created_at: str | None = None
        try:
            document = json.loads(layout.metadata.read_text(encoding="utf-8"))
            attempt_id = AttemptId.parse(str(document["attempt_id"]))
            exercise_id = ExerciseId(str(document["exercise_id"]))
            created_at = str(document["created_at"])
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return WorkspaceSummary(
            short_id=layout.root.name,
            attempt_id=attempt_id,
            exercise_id=exercise_id,
            created_at=created_at,
            size_bytes=_size_on_disk(layout.root),
        )


def _size_on_disk(root: Path) -> int:
    """Total size of a workspace, for a report that says whether collecting it is
    worth it. Tolerant of a tree being deleted underneath it — another process
    disposing of its own workspace mid-listing is a race nobody needs to lose.
    """
    total = 0
    for path in root.rglob("*"):
        try:
            if path.is_file():
                total += path.stat().st_size
        except OSError:
            continue
    return total
