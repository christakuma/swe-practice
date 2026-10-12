"""The real library, exported and read back.

In the content suite rather than in `tests/integration/` because the claim is
about `content/` itself, and PLAN.md §11 is specific about why that matters: a
content change is only covered by `-m content` and `tests/e2e`, and Phase 11's
one escaped defect was a property that held for three exercises and not for
fifty-four. Everything in `tests/integration/content/` asserts the pack format
against a two-exercise harness; this asserts it against the thing that ships.

**What only this file can catch** is a pack that is correct about every library
except the one in the repository: an exercise whose directory holds a file the
writer skips, a `curriculum.yaml` the derivation cannot reproduce, a kind that
arrived after the format was written. It is parametrized over nothing, because
the library is one object and the interesting assertions are about all of it at
once.

`tests/e2e/test_install_a_content_pack.py` carries the other half — that an
installed root can be *solved* from, which is the claim the catalogue port
cannot make.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.adapters.content import (
    FilesystemContentRepository,
    PackContentRepository,
    install_pack,
    verify_pack,
    write_pack,
)
from practice.adapters.content.pack import FIXTURE_LIB_DIRNAME
from practice.adapters.content.tracks import TRACKS_FILENAME
from practice.adapters.content.validation import validate_library
from practice.adapters.sandbox import LOCK_FILENAME
from practice.config import content_root
from practice.domain.exercise import ExerciseFilter, ExerciseKind

if TYPE_CHECKING:
    from pathlib import Path

    from practice.adapters.content import PackManifest
    from practice.domain.exercise import Exercise


@pytest.fixture(scope="module")
def library() -> Path:
    return content_root()


@pytest.fixture(scope="module")
def shipped(library: Path) -> list[Exercise]:
    return list(FilesystemContentRepository(library).list_exercises())


@pytest.fixture(scope="module")
def pack(tmp_path_factory: pytest.TempPathFactory, library: Path) -> Path:
    """The whole shipped library, exported once for every test in this file.

    Module-scoped because it walks several hundred files, and `--dist loadfile`
    is what keeps that one walk shared rather than repeated per worker (§11).
    """
    destination = tmp_path_factory.mktemp("pack") / "library.practicepack"
    write_pack(
        destination,
        content_root=library,
        exercises=FilesystemContentRepository(library).list_exercises(),
    )
    return destination


# --- the whole library survives the round trip -----------------------------


def test_the_shipped_library_exports(pack: Path) -> None:
    assert pack.is_file()


def test_the_pack_matches_its_own_manifest(pack: Path) -> None:
    """Verified against the real library, not a harness.

    The failure this rules out is a writer that hashes what it meant to put in
    rather than what it put in — which no two-exercise fixture would show,
    because the two numbers only diverge once something is skipped.
    """
    assert verify_pack(pack) == ()


def test_every_shipped_exercise_is_in_the_pack(
    pack: Path, shipped: list[Exercise]
) -> None:
    packed = PackContentRepository(pack).list_exercises()

    assert [str(found.id) for found in packed] == [str(found.id) for found in shipped]


def test_the_pack_rebuilds_every_shipped_aggregate_exactly(
    pack: Path, shipped: list[Exercise]
) -> None:
    """Whole `Exercise` values, so one assertion covers every field of every
    check of every spec across the entire library.
    """
    assert list(PackContentRepository(pack).list_exercises()) == shipped


def test_every_kind_in_the_library_survives_the_round_trip(
    pack: Path, shipped: list[Exercise]
) -> None:
    """A format written against two kinds and shipped with three.

    Stated as a property of the library rather than a list of kinds, so a
    fourth exercise kind fails this on the day it is added instead of being
    quietly absent from every pack — the same move
    `test_the_first_screen_of_the_curriculum_offers_every_kind` makes.
    """
    packed = PackContentRepository(pack).list_exercises()

    assert {found.kind for found in packed} == {found.kind for found in shipped}
    assert {found.kind for found in shipped} == set(ExerciseKind)


def test_the_pack_carries_the_shared_fixture_library(pack: Path) -> None:
    """24 scenarios source it, and it is not inside any exercise directory."""
    manifest = PackContentRepository(pack).manifest()

    assert f"{FIXTURE_LIB_DIRNAME}/fixture_lib.sh" in manifest.digests


def test_the_pack_carries_the_lock_file(pack: Path) -> None:
    """Without it the installed root cannot be held to its own determinism."""
    manifest = PackContentRepository(pack).manifest()

    assert LOCK_FILENAME in manifest.digests


def test_exporting_twice_gives_identical_bytes(
    tmp_path: Path, library: Path, shipped: list[Exercise]
) -> None:
    """The determinism claim at full size, where a single varying field shows.

    `tests/integration/content/` asserts this over two exercises; a timestamp
    or a mode leaking in from the filesystem is likelier to show up across
    three hundred files from three tracks.
    """
    first = tmp_path / "first.practicepack"
    second = tmp_path / "second.practicepack"

    write_pack(first, content_root=library, exercises=shipped)
    write_pack(second, content_root=library, exercises=shipped)

    assert first.read_bytes() == second.read_bytes()


# --- an installed pack is a library -----------------------------------------


def test_an_installed_pack_validates(
    tmp_path: Path, library: Path, shipped: list[Exercise]
) -> None:
    """The claim the derived indexes exist for, made with the real auditor.

    `practice validate` is one of the two commands CI runs over `content/`, and
    an installed pack has to pass it for the same reasons the source does: the
    curriculum must name every exercise exactly once and nothing that is not
    there.
    """
    destination = tmp_path / "library.practicepack"
    write_pack(destination, content_root=library, exercises=shipped)
    into = tmp_path / "installed"
    install_pack(destination, into)

    report = validate_library(into)

    assert report.ok, [report.problems, [found.problems for found in report.failures]]
    assert len(report.exercises) == len(shipped)


def test_an_installed_subset_is_a_library_in_its_own_right(
    tmp_path: Path, library: Path
) -> None:
    """The finding, at full size and in the command that would have caught it.

    A pack of part of the library that carried the whole `curriculum.yaml`
    installs to a root `validate_library` reports as naming fifty-four
    exercises that are not there. Here the SQL track alone is exported and the
    installed root audits clean.
    """
    on_disk = FilesystemContentRepository(library)
    drills = on_disk.list_exercises(
        ExerciseFilter(kinds=frozenset({ExerciseKind.SQL_DRILL}))
    )
    destination = tmp_path / "sql.practicepack"
    write_pack(destination, content_root=library, exercises=drills)
    into = tmp_path / "installed"
    install_pack(destination, into)

    report = validate_library(into)

    assert report.ok, [report.problems, [found.problems for found in report.failures]]
    assert len(report.exercises) == len(drills)


def test_an_installed_library_is_byte_identical_to_the_source(
    tmp_path: Path, library: Path, shipped: list[Exercise]
) -> None:
    """Every exercise file, compared as bytes. The line-ending claim, directly.

    A fixture that gained CRLF in transit builds different commit hashes, and
    `fixtures.lock` would then fail on the installed root for a reason that
    looks like a broken environment. Comparing the bytes says it here instead,
    in a test that needs no git and takes no time — `tests/e2e` runs the
    fixtures themselves.

    **The three derived indexes are left out by name**, because they are the
    files a pack regenerates rather than copies and so are *meant* to differ:
    each carries a header saying it is derived. `tracks.yaml` became the third
    in Phase 20, and this test is what found that — it failed in the full suite
    with the new file in `differing`, which is the right reading of a pack that
    now writes one more index. What it protects is everything else: no
    *exercise* file may change by a byte.
    """
    destination = tmp_path / "library.practicepack"
    write_pack(destination, content_root=library, exercises=shipped)
    into = tmp_path / "installed"
    manifest: PackManifest = install_pack(destination, into)

    differing = [
        name
        for name in manifest.digests
        if name not in {"curriculum.yaml", LOCK_FILENAME, TRACKS_FILENAME}
        and (library / name).read_bytes() != (into / name).read_bytes()
    ]

    assert differing == []
