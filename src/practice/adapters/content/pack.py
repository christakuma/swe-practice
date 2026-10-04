"""A content pack: one library, as one file, with its own digests.

PLAN.md §13's menu offers *exportable content packs* as "a content repository
adapter", and this module is the format half of that. A pack is a zip holding
`pack.yaml`, a `curriculum.yaml`, a `fixtures.lock`, the shared fixture bash and
one directory per exercise — which is to say it is a *library*, laid out exactly
as a content root is, plus a manifest that says what should be inside and what
each file's bytes hash to.

**It is a zip rather than a bespoke container**, so anybody can open one with the
tool they already have and read the exercises out of it. That is a feature of a
teaching tool and not a concession: the whole content layer is plain text on
purpose ([ADR 0004](../../../../docs/adr/0004-content-as-declarative-data.md)),
and a pack that needed `practice` to be inspected would be the first part of the
library a stranger could not read.

**Written deterministically, because the alternative undoes Phase 3.** A zip
records a modification time and a permission mode per entry, and both vary by
machine — so the same library would export to different bytes on Linux and
Windows, and a pack could not be checksummed, diffed or compared across
platforms. Every entry therefore gets a fixed timestamp and a fixed mode, the
entries are written in sorted order, and the bytes are copied as bytes rather
than as text. The last of those is the line-ending gotcha `.gitattributes`
exists for: a fixture read in text mode on Windows and written back would gain
CRLF, and a scenario's commit hashes would stop matching `fixtures.lock` —
making a pack a thing that silently breaks the determinism claim it is supposed
to carry.

**The indexes are derived, not copied, and that is the one thing a pack cannot
do naively.** `curriculum.yaml` and `fixtures.lock` are both per-exercise
indexes over the whole library, so a pack of *some* of it that carried them
verbatim would install to a content root that `practice validate` rejects
(a manifest naming exercises that are not on disk) and that `practice fixtures
--check` rejects (a lock entry with no exercise). Both are regenerated from the
selection instead, which means an exported subset is a library in its own right
rather than a library with holes in it.

The derived `curriculum.yaml` loses the hand-written reasoning at the top of the
real one, which is a genuine if small loss, so it gets a header saying it is
derived and where the original lives — the same move `fixtures.lock` has made
since Phase 3.

**The `fixtures.lock` serialiser is imported from `adapters/sandbox/`**, which
is a content module reaching sideways into another adapter package for the first
time. The alternative is a second copy of the lock file's YAML shape in here,
and a format with two writers is a format that will have two spellings. What it
costs is that `practice.adapters.sandbox.fixture_lock` — and so, transitively,
the provisioner — is now in the content package's import graph; nothing executes
as a result, and `render` and `parse` are pure functions over text.
"""

from __future__ import annotations

import hashlib
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Final

import yaml

from practice.adapters.content.curriculum import (
    CURRICULUM_FILENAME,
    Curriculum,
    Track,
    load_curriculum,
)
from practice.adapters.content.errors import ContentError
from practice.adapters.sandbox.fixture_lock import LOCK_FILENAME, parse, render
from practice.domain.errors import InvalidValueError
from practice.domain.exercise import GitScenarioSpec
from practice.domain.ids import ExerciseId

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping, Sequence

    from practice.domain.exercise import Exercise

__all__ = [
    "FIXTURE_LIB_DIRNAME",
    "MANIFEST_FILENAME",
    "PACK_FORMAT",
    "PACK_SUFFIX",
    "PackManifest",
    "install_pack",
    "pack_location",
    "read_manifest",
    "verify_pack",
    "write_pack",
]

#: The format number in `pack.yaml`. Bumped when a pack written by this version
#: would be misread by an older one — which is why `read_manifest` refuses a
#: number it does not know rather than doing its best with it.
PACK_FORMAT: Final = 1

MANIFEST_FILENAME: Final = "pack.yaml"

#: Any path works; this is what `--out` defaults to and what the docs name. A
#: suffix of its own rather than `.zip` so that a pack is recognisable as one,
#: and the module docstring is where "it is still a zip" is promised.
PACK_SUFFIX: Final = ".practicepack"

#: The shared fixture bash every git scenario sources, as a directory under the
#: content root. Carried whenever the source library has one, even by a pack
#: with no scenarios in it: a content root missing it is a root where the next
#: scenario added fails to provision, and the few kilobytes are not worth the
#: conditional.
FIXTURE_LIB_DIRNAME: Final = "_lib"

#: Entries never carried into a pack. `__pycache__` is the one that matters: a
#: kata's `tests.py` is importable, so anything that runs it from the content
#: tree leaves bytecode beside it, and a pack that copied whatever it found
#: would be non-deterministic for reasons nobody could see in the diff.
_EXCLUDED_NAMES: Final = frozenset({"__pycache__"})
_EXCLUDED_SUFFIXES: Final = (".pyc", ".pyo")

#: A fixed DOS timestamp for every entry: 1980-01-01, the earliest a zip can
#: express. Not "now", because a pack has to be byte-identical across machines
#: and runs, and a recorded time is the one field guaranteed to differ.
_FIXED_TIMESTAMP: Final = (1980, 1, 1, 0, 0, 0)

#: `0o644` in the high half of `external_attr`, where zip keeps a unix mode.
#: Fixed for the same reason as the timestamp: a umask is a property of the
#: machine that ran the export.
_FIXED_MODE: Final = 0o644 << 16

_CURRICULUM_HEADER: Final = """\
# The order this pack offers its exercises in -- derived, not hand-written.
#
# Generated by `practice pack`. A pack is a library in its own right, so it
# carries its own manifest rather than the source library's: a pack of part of
# a library that copied the whole ordering would install to a content root that
# `practice validate` refuses, naming exercises that are not there.
#
# The reasoning behind the order, and the comments that go with it, live in the
# source library's own curriculum.yaml.
"""


def pack_location(archive: Path, member: str) -> str:
    """How a file inside a pack is named in an error. `pack!path/to/file`.

    The `!` is the convention Java and Python both use for a path into an
    archive, and it is the reason `ContentError` accepts a `str`: this is a
    location worth printing exactly and not a path on this machine.
    """
    return f"{archive.name}!{member}"


@dataclass(frozen=True, slots=True)
class PackManifest:
    """What a pack says is inside it, and what each file's bytes hash to.

    `exercises` is in curriculum order rather than sorted, because it is the
    order the pack is meant to be worked through and re-deriving it from the
    packed `curriculum.yaml` would make the manifest the second-best source of
    something it can simply state.

    `digests` is keyed by archive-relative POSIX path and covers every file in
    the pack except `pack.yaml` itself. A manifest that hashed itself could not
    be written, and the usual answer — hash everything else, then hash the
    manifest separately — buys tamper detection, which is not what this is for.
    **It is for corruption and truncation**, the two things that actually happen
    to a file somebody emailed: a pack is not signed and a determined editor can
    rewrite both a file and its digest.
    """

    format: int
    exercises: tuple[ExerciseId, ...]
    digests: Mapping[str, str]
    created_with: str = ""

    def as_document(self) -> dict[str, object]:
        """The YAML shape. Sorted digests, so a diff only shows a real change."""
        return {
            "format": self.format,
            "created_with": self.created_with,
            "exercises": [exercise_id.value for exercise_id in self.exercises],
            "digests": dict(sorted(self.digests.items())),
        }


def write_pack(
    destination: Path,
    *,
    content_root: Path,
    exercises: Sequence[Exercise],
    created_with: str = "",
) -> PackManifest:
    """Write `exercises` and their files to `destination` as a pack.

    Takes the exercises rather than a filter, because deciding *which* of them
    to export is a question about a library and this function's job is the
    archive. The caller has a `ContentRepository` and `ExerciseFilter` for that,
    which is also what keeps "in curriculum order" true here without this module
    knowing what an order is.

    Raises `ContentError` if the selection is empty. A pack of nothing is a file
    that installs to a content root `validate_library` reports as holding no
    exercises, which is a worse way to find out.
    """
    if not exercises:
        raise ContentError(destination, ["a pack must hold at least one exercise"])

    members = dict(_derived(content_root, exercises))
    for exercise in exercises:
        directory = content_root / exercise.id.value
        if not directory.is_dir():
            raise ContentError(
                directory, [f"{exercise.id}: named by the library but not on disk"]
            )
        for path in _files_under(directory):
            members[_member(path.relative_to(content_root))] = path.read_bytes()

    library = content_root / FIXTURE_LIB_DIRNAME
    if library.is_dir():
        for path in _files_under(library):
            members[_member(path.relative_to(content_root))] = path.read_bytes()

    manifest = PackManifest(
        format=PACK_FORMAT,
        exercises=tuple(exercise.id for exercise in exercises),
        digests={name: _digest(body) for name, body in members.items()},
        created_with=created_with,
    )
    members[MANIFEST_FILENAME] = _render_manifest(manifest)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        # Sorted, so the archive's own entry order is a property of the content
        # rather than of the dict insertion above.
        for name in sorted(members):
            entry = zipfile.ZipInfo(filename=name, date_time=_FIXED_TIMESTAMP)
            entry.external_attr = _FIXED_MODE
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, members[name])

    return manifest


def read_manifest(archive: Path) -> PackManifest:
    """The pack's own account of itself. Raises `ContentError` if unreadable.

    Deliberately separate from `verify_pack`: reading the manifest is what
    `practice pack --check` does *first*, and a pack whose manifest cannot be
    parsed has one problem worth reporting rather than one per file.
    """
    located = pack_location(archive, MANIFEST_FILENAME)
    if not archive.is_file():
        raise ContentError(archive, ["no such file"])
    try:
        with zipfile.ZipFile(archive) as opened:
            raw = opened.read(MANIFEST_FILENAME).decode("utf-8")
    except KeyError as exc:
        raise ContentError(
            archive, [f"is not a content pack: it holds no {MANIFEST_FILENAME}"]
        ) from exc
    except (OSError, zipfile.BadZipFile) as exc:
        raise ContentError(archive, [f"cannot be read as a zip: {exc}"]) from exc
    except UnicodeDecodeError as exc:
        raise ContentError(located, ["is not UTF-8 text"]) from exc

    try:
        document: object = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ContentError(located, [f"is not valid YAML: {exc}"]) from exc
    return _manifest_from(document, located_at=located)


def verify_pack(archive: Path) -> tuple[str, ...]:
    """Every way the pack's contents disagree with its manifest. Empty is good.

    Returns rather than raises, for the reason `validate_exercise` does: one run
    should report every problem, and a truncated download is not one file short.
    """
    manifest = read_manifest(archive)
    problems: list[str] = []

    with zipfile.ZipFile(archive) as opened:
        present = {name for name in opened.namelist() if not name.endswith("/")} - {
            MANIFEST_FILENAME
        }

        for name, expected in sorted(manifest.digests.items()):
            if name not in present:
                problems.append(f"{name}: in the manifest but not in the pack")
                continue
            found = _digest(opened.read(name))
            if found != expected:
                problems.append(
                    f"{name}: digest is {found[:12]}, manifest says {expected[:12]}"
                )

        for name in sorted(present - set(manifest.digests)):
            problems.append(f"{name}: in the pack but not in the manifest")

    return tuple(problems)


def install_pack(archive: Path, into: Path) -> PackManifest:
    """Verify a pack and extract it to `into`, which becomes a content root.

    **Verification first, and the whole archive or nothing.** A pack half
    extracted because the digests failed on the thirtieth file leaves a
    directory that looks like a library and is not one, and the next thing
    anybody runs against it reports a missing exercise rather than a corrupt
    download.

    Extraction is by name through `ZipFile.open` rather than `extractall`,
    because `extractall` honours whatever path the archive asked for — and a
    member named `../../etc/thing` is a real zip, however unlikely it is to
    arrive here. `_member` refuses one on the way out; this refuses one on the
    way in, which is the same duplication the aggregate and the schema do
    (PLAN.md §5.4).
    """
    problems = verify_pack(archive)
    if problems:
        raise ContentError(archive, problems)

    manifest = read_manifest(archive)
    with zipfile.ZipFile(archive) as opened:
        for name in sorted(manifest.digests):
            target = _resolved(into, name, archive)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(opened.read(name))

    # Not derived here: the pack carries its own, because they were derived
    # when it was written and re-deriving them on install would let an
    # installed root disagree with the pack it came from.
    return manifest


# --- the derived indexes ---------------------------------------------------


def _derived(
    content_root: Path, exercises: Sequence[Exercise]
) -> Iterator[tuple[str, bytes]]:
    """`curriculum.yaml` and `fixtures.lock`, narrowed to this selection."""
    selected = {exercise.id for exercise in exercises}
    yield (
        CURRICULUM_FILENAME,
        _render_curriculum(_narrowed(load_curriculum(content_root), selected)),
    )
    yield (LOCK_FILENAME, _narrowed_lock(content_root, exercises))


def _narrowed(curriculum: Curriculum, selected: Iterable[ExerciseId]) -> Curriculum:
    """The same ordering with everything unselected removed, tracks included.

    A track left holding nothing is dropped rather than written empty, because
    `_track` refuses a track with no exercises — so a pack that wrote one could
    not be loaded by the parser that wrote it.
    """
    keep = frozenset(selected)
    tracks = tuple(
        Track(
            name=track.name,
            title=track.title,
            exercises=tuple(found for found in track.exercises if found in keep),
        )
        for track in curriculum.tracks
    )
    return Curriculum(tracks=tuple(track for track in tracks if track.exercises))


def _render_curriculum(curriculum: Curriculum) -> bytes:
    document = {
        "tracks": [
            {
                "name": track.name,
                "title": track.title,
                "exercises": [exercise_id.value for exercise_id in track.exercises],
            }
            for track in curriculum.tracks
        ]
    }
    # `sort_keys=False`, so name/title/exercises stay in the order a reader
    # expects rather than alphabetical; the ordering itself is the data here.
    body = yaml.safe_dump(document, sort_keys=False, default_flow_style=False)
    return (_CURRICULUM_HEADER + body).encode("utf-8")


def _narrowed_lock(content_root: Path, exercises: Sequence[Exercise]) -> bytes:
    """The lock file's entries for the git scenarios in this selection.

    Written even when there are none, as a header and nothing else. `practice
    fixtures --check` refuses a content root with no lock file at all, so a
    katas-only pack that omitted it would install to a library one of the two
    CI commands could not run — and an empty lock is exactly right about a
    library with no fixtures in it.
    """
    scenarios = {
        exercise.id.value
        for exercise in exercises
        if isinstance(exercise.spec, GitScenarioSpec)
    }
    lock = content_root / LOCK_FILENAME
    recorded = parse(lock.read_text(encoding="utf-8")) if lock.is_file() else ()
    kept = [found for found in recorded if found.exercise_id in scenarios]
    return render(kept).encode("utf-8")


# --- archive paths and digests --------------------------------------------


def _files_under(directory: Path) -> Iterator[Path]:
    """Every file in the tree, excluding build droppings, in a stable order."""
    for path in sorted(directory.rglob("*")):
        parts = path.relative_to(directory).parts
        if any(part in _EXCLUDED_NAMES for part in parts):
            continue
        if path.suffix in _EXCLUDED_SUFFIXES or not path.is_file():
            continue
        yield path


def _member(relative: Path) -> str:
    """A content-root-relative path as an archive member name.

    Forward slashes always, because a zip's member names are POSIX and a pack
    written on Windows must be readable on Linux — the same reason `RepoQuery`
    forward-slashes every path it reports.
    """
    name = relative.as_posix()
    if name.startswith("/") or ".." in relative.parts:
        raise ContentError(relative, ["cannot be put in a pack: it escapes the root"])
    return name


def _resolved(into: Path, member: str, archive: Path) -> Path:
    """Where a member lands under `into`, refusing one that escapes it."""
    name = PurePosixPath(member)
    if name.is_absolute() or ".." in name.parts:
        raise ContentError(
            pack_location(archive, member),
            ["names a path outside the pack; refusing to extract it"],
        )
    return into.joinpath(*name.parts)


def _digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _render_manifest(manifest: PackManifest) -> bytes:
    return yaml.safe_dump(manifest.as_document(), sort_keys=False).encode("utf-8")


def _manifest_from(document: object, *, located_at: str) -> PackManifest:
    """Validate the manifest, collecting every problem rather than the first."""
    if not isinstance(document, dict):
        raise ContentError(located_at, ["must be a mapping of keys"])

    problems: list[str] = []
    found = document.get("format")
    if found != PACK_FORMAT:
        problems.append(
            f"format: {found!r} is not a format this version can read "
            f"(it reads {PACK_FORMAT})"
        )

    exercises = tuple(_exercise_ids(document.get("exercises"), problems))
    digests = _digests(document.get("digests"), problems)
    created_with = document.get("created_with")
    if created_with is not None and not isinstance(created_with, str):
        problems.append("created_with: must be a string")

    if problems:
        raise ContentError(located_at, problems)
    return PackManifest(
        format=PACK_FORMAT,
        exercises=exercises,
        digests=digests,
        created_with=created_with if isinstance(created_with, str) else "",
    )


def _exercise_ids(value: object, problems: list[str]) -> Iterator[ExerciseId]:
    if not isinstance(value, list) or not value:
        problems.append("exercises: must be a non-empty list")
        return
    for raw in value:
        if not isinstance(raw, str):
            problems.append(f"exercises: {raw!r} is not an exercise id")
            continue
        try:
            yield ExerciseId(raw)
        except InvalidValueError as exc:
            problems.append(f"exercises: {raw!r} {exc}")


def _digests(value: object, problems: list[str]) -> dict[str, str]:
    if not isinstance(value, dict) or not value:
        problems.append("digests: must be a non-empty mapping of path to sha256")
        return {}
    found: dict[str, str] = {}
    for name, digest in value.items():
        if not isinstance(name, str) or not isinstance(digest, str):
            problems.append(f"digests: {name!r}: {digest!r} is not a path and a digest")
            continue
        found[name] = digest
    return found
