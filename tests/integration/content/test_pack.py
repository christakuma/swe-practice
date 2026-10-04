"""The pack format: a library as one deterministic file, with its own digests.

Integration rather than unit tests, for the reason
`test_filesystem_repository.py` is: every claim here is about bytes on a disk —
that two exports agree, that a copied fixture keeps its line endings, that a
corrupt pack is refused before anything is written. A fake filesystem would be
testing the fake.
"""

from __future__ import annotations

import hashlib
import zipfile
from typing import TYPE_CHECKING

import pytest

from practice.adapters.content import ContentError, FilesystemContentRepository
from practice.adapters.content.pack import (
    FIXTURE_LIB_DIRNAME,
    MANIFEST_FILENAME,
    PACK_FORMAT,
    install_pack,
    read_manifest,
    verify_pack,
    write_pack,
)
from practice.adapters.sandbox import LOCK_FILENAME

from ..conftest import a_kata, a_scenario

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.exercise import Exercise

    from ..conftest import WriteExercise


@pytest.fixture
def stocked(library: Path, write_exercise: WriteExercise) -> Path:
    """One of each kind, plus the two files a real content root has beside them.

    The lock file and `_lib/` are written here rather than left out because they
    are the two things a pack has to do something *other* than copy, and a
    harness without them would make every test in this file pass on a library
    that does not look like the real one.
    """
    write_exercise(a_kata())
    write_exercise(a_scenario())
    (library / FIXTURE_LIB_DIRNAME).mkdir()
    (library / FIXTURE_LIB_DIRNAME / "fixture_lib.sh").write_text(
        "#!/usr/bin/env bash\n", encoding="utf-8", newline=""
    )
    (library / LOCK_FILENAME).write_text(
        "git/undo-a-commit:\n  aliases:\n    c1: abc123\n  refs:\n    main: abc123\n",
        encoding="utf-8",
        newline="",
    )
    return library


@pytest.fixture
def exercises(stocked: Path) -> list[Exercise]:
    return list(FilesystemContentRepository(stocked).list_exercises())


# --- what a pack holds -----------------------------------------------------


def test_a_pack_holds_every_file_of_every_exercise(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    written = write_pack(
        tmp_path / "out.practicepack", content_root=stocked, exercises=exercises
    )

    assert "katas/two-sum/exercise.yaml" in written.digests
    assert "katas/two-sum/notes.md" in written.digests
    assert "git/undo-a-commit/fixture.sh" in written.digests
    assert "git/undo-a-commit/solution.cmds" in written.digests


def test_a_pack_carries_the_shared_fixture_library(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    """Without it a scenario cannot provision, and `_lib` is not an exercise."""
    written = write_pack(
        tmp_path / "out.practicepack", content_root=stocked, exercises=exercises
    )

    assert f"{FIXTURE_LIB_DIRNAME}/fixture_lib.sh" in written.digests


def test_a_pack_names_its_exercises_in_curriculum_order(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    """The manifest states the order rather than leaving it to be re-derived.

    `stocked` writes the kata first, so curriculum order and id order disagree
    — which is what makes this an assertion about the order and not about the
    sort.
    """
    written = write_pack(
        tmp_path / "out.practicepack", content_root=stocked, exercises=exercises
    )

    assert [str(found) for found in written.exercises] == [
        "katas/two-sum",
        "git/undo-a-commit",
    ]


def test_build_droppings_are_left_out(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    """A kata's `tests.py` is importable, so bytecode appears beside it.

    The reason this matters is not tidiness: a pack that copied whatever it
    found in the directory would stop being byte-identical the moment anything
    imported a kata's test file, and the diff would show a file nobody wrote.
    """
    cache = stocked / "katas" / "two-sum" / "__pycache__"
    cache.mkdir()
    (cache / "tests.cpython-313.pyc").write_bytes(b"\x00\x01")

    written = write_pack(
        tmp_path / "out.practicepack", content_root=stocked, exercises=exercises
    )

    assert not [name for name in written.digests if "__pycache__" in name]


def test_an_empty_selection_is_refused(tmp_path: Path, stocked: Path) -> None:
    """A pack of nothing installs to a root `validate` calls empty, later."""
    with pytest.raises(ContentError) as caught:
        write_pack(tmp_path / "out.practicepack", content_root=stocked, exercises=[])

    assert caught.value.problems == ("a pack must hold at least one exercise",)


# --- determinism -----------------------------------------------------------


def test_the_same_library_exports_to_the_same_bytes(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    """The Phase 3 determinism claim, extended to the pack that carries it.

    A zip records a timestamp and a mode per entry and both vary by machine, so
    this is the assertion that says they were pinned. Without it a pack could
    not be checksummed or compared across platforms, and CI running on Linux
    and Windows would have nothing to disagree about.
    """
    first = tmp_path / "first.practicepack"
    second = tmp_path / "second.practicepack"

    write_pack(first, content_root=stocked, exercises=exercises)
    write_pack(second, content_root=stocked, exercises=exercises)

    assert first.read_bytes() == second.read_bytes()


def test_entries_are_stored_in_sorted_order(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    """So the archive's own layout is a property of the content, not of a dict."""
    destination = tmp_path / "out.practicepack"
    write_pack(destination, content_root=stocked, exercises=exercises)

    with zipfile.ZipFile(destination) as archive:
        names = archive.namelist()

    assert names == sorted(names)


def test_a_fixture_keeps_its_line_endings(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    """The gotcha `.gitattributes` exists for, applied to the pack.

    A fixture read in text mode on Windows and written back would gain CRLF,
    and the commit hashes it builds would stop matching `fixtures.lock` — so a
    pack would silently break the one claim it is meant to carry across
    machines. Bytes in, bytes out.
    """
    fixture = stocked / "git" / "undo-a-commit" / "fixture.sh"
    fixture.write_bytes(b"#!/usr/bin/env bash\ngit init\n")
    destination = tmp_path / "out.practicepack"

    write_pack(destination, content_root=stocked, exercises=exercises)

    with zipfile.ZipFile(destination) as archive:
        assert archive.read("git/undo-a-commit/fixture.sh") == (
            b"#!/usr/bin/env bash\ngit init\n"
        )


# --- the derived indexes ---------------------------------------------------


def test_a_subset_pack_narrows_the_curriculum(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    """The finding this format turns on.

    A pack carrying the source library's whole `curriculum.yaml` would install
    to a content root `validate_library` refuses, because the manifest would
    name an exercise that is not there. So the ordering is regenerated from the
    selection, and an exported subset is a library in its own right.
    """
    katas = [found for found in exercises if str(found.id).startswith("katas/")]
    destination = tmp_path / "out.practicepack"

    write_pack(destination, content_root=stocked, exercises=katas)

    with zipfile.ZipFile(destination) as archive:
        ordering = archive.read("curriculum.yaml").decode("utf-8")
    assert "katas/two-sum" in ordering
    assert "git/undo-a-commit" not in ordering


def test_a_subset_pack_narrows_the_lock_file(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    """The same claim for the other index, which fails in a different command.

    A lock entry naming an exercise that is not in the library is what
    `practice fixtures --check` reports as "in fixtures.lock but no longer in
    the library" — a green-looking pack that fails the second CI gate.
    """
    katas = [found for found in exercises if str(found.id).startswith("katas/")]
    destination = tmp_path / "out.practicepack"

    write_pack(destination, content_root=stocked, exercises=katas)

    with zipfile.ZipFile(destination) as archive:
        lock = archive.read(LOCK_FILENAME).decode("utf-8")
    assert "git/undo-a-commit" not in lock


def test_a_pack_with_no_scenarios_still_carries_a_lock_file(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    """Empty, and present. `practice fixtures --check` refuses a root without one.

    So a katas-only pack that omitted it would install to a library one of the
    two CI commands could not run at all — and an empty lock is exactly right
    about a library with no fixtures in it.
    """
    katas = [found for found in exercises if str(found.id).startswith("katas/")]
    destination = tmp_path / "out.practicepack"

    written = write_pack(destination, content_root=stocked, exercises=katas)

    assert LOCK_FILENAME in written.digests


def test_a_library_with_no_lock_file_can_still_be_packed(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    """An author who has never run `fixtures --write` is not blocked from export."""
    (stocked / LOCK_FILENAME).unlink()

    written = write_pack(
        tmp_path / "out.practicepack", content_root=stocked, exercises=exercises
    )

    assert LOCK_FILENAME in written.digests


# --- the manifest ----------------------------------------------------------


def test_the_manifest_round_trips(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    destination = tmp_path / "out.practicepack"
    written = write_pack(
        destination, content_root=stocked, exercises=exercises, created_with="1.2.3"
    )

    read = read_manifest(destination)

    assert read.format == PACK_FORMAT
    assert read.exercises == written.exercises
    assert read.digests == written.digests
    assert read.created_with == "1.2.3"


def test_the_manifest_does_not_hash_itself(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    """It could not: the digest would have to be inside the file it covers."""
    destination = tmp_path / "out.practicepack"

    written = write_pack(destination, content_root=stocked, exercises=exercises)

    assert MANIFEST_FILENAME not in written.digests


def test_a_file_that_is_not_a_zip_is_refused(tmp_path: Path) -> None:
    rubbish = tmp_path / "out.practicepack"
    rubbish.write_bytes(b"not a zip at all")

    with pytest.raises(ContentError) as caught:
        read_manifest(rubbish)

    assert "cannot be read as a zip" in caught.value.problems[0]


def test_a_zip_with_no_manifest_is_not_a_pack(tmp_path: Path) -> None:
    plain = tmp_path / "out.practicepack"
    with zipfile.ZipFile(plain, "w") as archive:
        archive.writestr("katas/two-sum/exercise.yaml", "id: katas/two-sum\n")

    with pytest.raises(ContentError) as caught:
        read_manifest(plain)

    assert caught.value.problems == (
        f"is not a content pack: it holds no {MANIFEST_FILENAME}",
    )


def test_a_missing_pack_is_reported_as_such(tmp_path: Path) -> None:
    with pytest.raises(ContentError) as caught:
        read_manifest(tmp_path / "nope.practicepack")

    assert caught.value.problems == ("no such file",)


@pytest.mark.parametrize(
    ("manifest", "expected"),
    [
        pytest.param("[]", "must be a mapping of keys", id="not-a-mapping"),
        pytest.param(
            "format: 99\nexercises: [katas/two-sum]\ndigests: {a: b}\n",
            "is not a format this version can read",
            id="unknown-format",
        ),
        pytest.param(
            f"format: {PACK_FORMAT}\nexercises: []\ndigests: {{a: b}}\n",
            "exercises: must be a non-empty list",
            id="no-exercises",
        ),
        pytest.param(
            f"format: {PACK_FORMAT}\nexercises: [not-an-id]\ndigests: {{a: b}}\n",
            "'not-an-id'",
            id="bad-id",
        ),
        pytest.param(
            f"format: {PACK_FORMAT}\nexercises: [katas/two-sum]\ndigests: {{}}\n",
            "digests: must be a non-empty mapping",
            id="no-digests",
        ),
        pytest.param(
            f"format: {PACK_FORMAT}\nexercises: [katas/two-sum]\n"
            f"digests: {{a: b}}\ncreated_with: 7\n",
            "created_with: must be a string",
            id="bad-created-with",
        ),
    ],
)
def test_a_malformed_manifest_names_what_is_wrong(
    tmp_path: Path, manifest: str, expected: str
) -> None:
    """Every problem in one pass, located inside the archive it came from."""
    broken = tmp_path / "out.practicepack"
    with zipfile.ZipFile(broken, "w") as archive:
        archive.writestr(MANIFEST_FILENAME, manifest)

    with pytest.raises(ContentError) as caught:
        read_manifest(broken)

    assert any(expected in problem for problem in caught.value.problems)
    assert str(caught.value.path) == f"out.practicepack!{MANIFEST_FILENAME}"


# --- verification ----------------------------------------------------------


def test_a_good_pack_verifies(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    destination = tmp_path / "out.practicepack"
    write_pack(destination, content_root=stocked, exercises=exercises)

    assert verify_pack(destination) == ()


def test_an_edited_file_is_caught(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    """What the digests are actually for: corruption and truncation.

    Not tampering — a pack is not signed, and anyone who can rewrite a file can
    rewrite its digest. This is the damage a file takes in transit.
    """
    destination = tmp_path / "out.practicepack"
    write_pack(destination, content_root=stocked, exercises=exercises)
    _rewrite(destination, {"katas/two-sum/notes.md": b"something else"})

    problems = verify_pack(destination)

    assert len(problems) == 1
    assert problems[0].startswith("katas/two-sum/notes.md: digest is ")


def test_a_missing_file_is_caught(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    destination = tmp_path / "out.practicepack"
    write_pack(destination, content_root=stocked, exercises=exercises)
    _rewrite(destination, {"katas/two-sum/notes.md": None})

    assert verify_pack(destination) == (
        "katas/two-sum/notes.md: in the manifest but not in the pack",
    )


def test_a_file_the_manifest_never_heard_of_is_caught(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    """The direction a digest check cannot catch on its own.

    Hashing only what the manifest lists would bless an archive with an extra
    exercise smuggled into it, because nothing would ever read that entry.
    """
    destination = tmp_path / "out.practicepack"
    write_pack(destination, content_root=stocked, exercises=exercises)
    _rewrite(destination, {"katas/extra/exercise.yaml": b"id: katas/extra\n"})

    assert verify_pack(destination) == (
        "katas/extra/exercise.yaml: in the pack but not in the manifest",
    )


# --- installation ----------------------------------------------------------


def test_installing_lays_out_a_content_root(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    destination = tmp_path / "out.practicepack"
    write_pack(destination, content_root=stocked, exercises=exercises)

    installed = install_pack(destination, tmp_path / "root")

    root = tmp_path / "root"
    assert (root / "curriculum.yaml").is_file()
    assert (root / LOCK_FILENAME).is_file()
    assert (root / "katas" / "two-sum" / "exercise.yaml").is_file()
    assert (root / FIXTURE_LIB_DIRNAME / "fixture_lib.sh").is_file()
    assert len(installed.exercises) == 2


def test_a_corrupt_pack_is_refused_before_anything_is_written(
    tmp_path: Path, stocked: Path, exercises: list[Exercise]
) -> None:
    """Half a library looks like a library and is not one.

    The next command run against it reports a missing exercise rather than a
    corrupt download, which is the wrong problem to be shown.
    """
    destination = tmp_path / "out.practicepack"
    write_pack(destination, content_root=stocked, exercises=exercises)
    _rewrite(destination, {"katas/two-sum/notes.md": b"edited"})
    into = tmp_path / "root"

    with pytest.raises(ContentError):
        install_pack(destination, into)

    assert not into.exists()


def test_a_member_that_escapes_the_root_is_refused(tmp_path: Path) -> None:
    """A zip can name `../../anything`. `extractall` would honour it.

    Refused on the way in as well as on the way out, which is the same
    duplication the aggregate and the schema do deliberately (PLAN.md §5.4).
    """
    hostile = tmp_path / "out.practicepack"
    body = b"id: katas/two-sum\n"
    with zipfile.ZipFile(hostile, "w") as archive:
        archive.writestr(
            MANIFEST_FILENAME,
            f"format: {PACK_FORMAT}\nexercises: [katas/two-sum]\n"
            f"digests:\n  '../escaped.yaml': "
            f"{hashlib.sha256(body).hexdigest()}\n",
        )
        archive.writestr("../escaped.yaml", body)

    with pytest.raises(ContentError) as caught:
        install_pack(hostile, tmp_path / "root")

    assert caught.value.problems == (
        "names a path outside the pack; refusing to extract it",
    )


def _rewrite(destination: Path, changes: dict[str, bytes | None]) -> None:
    """Rebuild a pack with files replaced, removed or added, manifest untouched.

    A helper rather than six near-identical bodies, because `zipfile` cannot
    edit an entry in place and every corruption test needs the same surgery.
    Leaving the manifest alone is the point: these tests are about the pack's
    *contents* disagreeing with what it says is inside it.
    """
    with zipfile.ZipFile(destination) as archive:
        kept = {name: archive.read(name) for name in archive.namelist()}
    for name, body in changes.items():
        if body is None:
            kept.pop(name, None)
        else:
            kept[name] = body
    with zipfile.ZipFile(destination, "w") as archive:
        for name in sorted(kept):
            archive.writestr(name, kept[name])
