"""`ContentRepository` over a pack, without extracting it.

**The reason Phase 16 was worth taking.** PLAN.md §13 requires every port to
earn its keep with at least two real or test implementations, and says the honest
response to a port with one is to delete it. `ContentRepository` had
`FilesystemContentRepository` and a fake, which is the arrangement §13 accepts
and the weakest version of it: a protocol whose only real implementation is the
one it was extracted from has not been shown to abstract anything. This is the
second, and the thing it proves is that the port's two methods are enough to
serve a library from a source that is not a directory.

**It reads the archive rather than unpacking it**, which is the whole point. A
repository that extracted to a temporary directory and delegated to
`FilesystemContentRepository` would be an abstraction forwarding one call
unchanged — the thing PLAN.md §13 names as the fastest way to ruin this project
— and it would prove only that `zipfile.extractall` works. So the parsing goes
through `loader.parse_exercise_file` and `curriculum.parse_curriculum`, the two
text-taking functions that exist for exactly this, and the directory is never
created.

**Order comes from the packed `curriculum.yaml`, not from the manifest**, even
though the manifest lists the exercises in curriculum order and reading it would
be fewer lines. Two orderings in one file is one ordering too many: if this
repository obeyed the manifest, a packed library and the same pack *installed*
to a content root could list their exercises differently, and nothing would ever
say so. One mechanism, one answer, and `tests/integration/content/` holds both
implementations to it.

**It trusts the manifest's digests rather than checking them.** Verification
reads and hashes every file in the pack, which is `practice pack --check`'s
whole job and is not something to do on the way to rendering a list of titles.
The division is the same one `loader` and `validation` draw: this answers "what
is in here?", and whether the pack arrived intact is a different question with
its own command.

**What this cannot do is let anybody solve anything**, and that is the finding
rather than an omission. `SubprocessSandboxProvisioner` takes a `content_root:
Path` and resolves `content_root / exercise_id` itself, so a fixture, a stub and
a `tests.py` reach a workspace by being copied from a directory and never
through this port. A pack-backed library can therefore be browsed, filtered,
counted and scheduled, and the moment an attempt starts it needs files on a
disk. `install_pack` is the answer, and
[ADR 0021](../../../../docs/adr/0021-content-packs-install-rather-than-mount.md)
is why that is the right one rather than a widened port.
"""

from __future__ import annotations

import zipfile
from typing import TYPE_CHECKING

from practice.adapters.content.curriculum import (
    CURRICULUM_FILENAME,
    parse_curriculum,
)
from practice.adapters.content.errors import ContentError
from practice.adapters.content.loader import (
    EXERCISE_FILENAME,
    NOTES_FILENAME,
    build_exercise,
    parse_exercise_file,
)
from practice.adapters.content.pack import pack_location, read_manifest

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from practice.adapters.content.curriculum import Curriculum
    from practice.adapters.content.pack import PackManifest
    from practice.domain.exercise import Exercise, ExerciseFilter
    from practice.domain.ids import ExerciseId

__all__ = ["PackContentRepository"]


class PackContentRepository:
    """Satisfies `practice.domain.ports.ContentRepository` from a pack file.

    Structurally, not by inheritance — the port is a `Protocol`, so this class
    does not import it and the dependency arrow keeps pointing inward (ADR
    0002).

    **Loaded once, then cached**, and the archive is not held open in between.
    Keeping a `ZipFile` alive for the life of the repository would hold a file
    handle on a pack the user may want to move or delete, and on Windows it
    would stop them — for no gain, because content is read-only at runtime and
    one pass reads all of it.
    """

    def __init__(self, archive: Path) -> None:
        self._archive = archive
        self._exercises: dict[ExerciseId, Exercise] | None = None

    @property
    def archive(self) -> Path:
        return self._archive

    def manifest(self) -> PackManifest:
        """What the pack says is inside it. Raises `ContentError` if unreadable."""
        return read_manifest(self._archive)

    def list_exercises(
        self, criteria: ExerciseFilter | None = None
    ) -> Sequence[Exercise]:
        """Every exercise the filter accepts, in the pack's curriculum order.

        The filtering is `ExerciseFilter.matches`, which lives in the domain so
        that this repository, the filesystem one and any fake cannot disagree
        about what a filter means — the drift that stops a second
        implementation being evidence of anything.
        """
        exercises = self._loaded()
        if criteria is None:
            return list(exercises.values())
        return [
            exercise for exercise in exercises.values() if criteria.matches(exercise)
        ]

    def get(self, exercise_id: ExerciseId) -> Exercise | None:
        """The exercise, or `None` if this pack does not hold it."""
        return self._loaded().get(exercise_id)

    def _loaded(self) -> dict[ExerciseId, Exercise]:
        """Read the whole pack in one pass, in curriculum order.

        A dict, and insertion order is the curriculum's, which is what lets
        `list_exercises` return `.values()` without re-sorting. The filesystem
        repository sorts because it discovers exercises by walking a directory
        and the walk's order is the filesystem's; here the order is known before
        anything is read.
        """
        if self._exercises is not None:
            return self._exercises

        with zipfile.ZipFile(self._archive) as archive:
            ordering = self._curriculum(archive)
            found = {}
            for exercise_id in ordering.exercise_ids:
                exercise = self._exercise(archive, exercise_id)
                found[exercise.id] = exercise
        self._exercises = found
        return found

    def _curriculum(self, archive: zipfile.ZipFile) -> Curriculum:
        """The packed manifest. A pack without one is a pack with no order.

        An error rather than a fallback, exactly as on disk: the alternative is
        ordering a library by accident when a file is missing, which is the bug
        `curriculum.py` was written to remove.
        """
        return parse_curriculum(
            self._read(archive, CURRICULUM_FILENAME),
            located_at=pack_location(self._archive, CURRICULUM_FILENAME),
        )

    def _exercise(self, archive: zipfile.ZipFile, exercise_id: ExerciseId) -> Exercise:
        """One exercise, from two entries. Notes are optional; the YAML is not."""
        member = f"{exercise_id.value}/{EXERCISE_FILENAME}"
        located = pack_location(self._archive, member)
        parsed = parse_exercise_file(self._read(archive, member), located_at=located)
        notes = f"{exercise_id.value}/{NOTES_FILENAME}"
        return build_exercise(
            parsed,
            exercise_id=exercise_id,
            notes=self._read(archive, notes) if notes in archive.namelist() else "",
            located_at=located,
        )

    def _read(self, archive: zipfile.ZipFile, member: str) -> str:
        """One entry as UTF-8 text, naming the pack when it is not there.

        A missing entry is a `ContentError` rather than a `KeyError` for the
        reason the whole content layer gives: the thing a user has to be told is
        which file is wrong and where it lives, and a traceback from `zipfile`
        names neither.
        """
        located = pack_location(self._archive, member)
        try:
            raw = archive.read(member)
        except KeyError as exc:
            raise ContentError(located, ["no such file in the pack"]) from exc
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ContentError(located, ["is not UTF-8 text"]) from exc
