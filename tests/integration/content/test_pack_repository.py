"""`PackContentRepository`, and both real `ContentRepository` implementations
asked the same questions.

The content layer's counterpart to `tests/integration/sql/test_conformance.py`,
and it exists for the stronger of that file's two reasons. There it is that unit
tests against a fake are only evidence if the fake answers like the engine.
Here it is PLAN.md §13's rule itself: a port with one real implementation has
not been shown to abstract anything, so the claim worth testing is not that this
class works but that **the two disagree about nothing** — and that the pack is a
faithful enough copy for the second answer to be the same as the first.

Conformance is over the same library exported and read back, rather than over
two hand-written fixtures, because that is the only version of the claim anybody
cares about: send somebody your library and they see your library.
"""

from __future__ import annotations

import zipfile
from typing import TYPE_CHECKING

import pytest

from practice.adapters.content import (
    ContentError,
    FilesystemContentRepository,
    PackContentRepository,
    write_pack,
)
from practice.adapters.content.pack import MANIFEST_FILENAME, PACK_FORMAT
from practice.domain.exercise import Difficulty, ExerciseFilter, ExerciseKind
from practice.domain.ids import ExerciseId

from ..conftest import a_drill, a_kata, a_scenario

if TYPE_CHECKING:
    from pathlib import Path

    from practice.domain.ports import ContentRepository

    from ..conftest import WriteExercise


@pytest.fixture
def stocked(library: Path, write_exercise: WriteExercise) -> Path:
    """One of each kind, written so that curriculum order is not id order."""
    write_exercise(a_kata())
    write_exercise(a_scenario())
    write_exercise(a_drill())
    return library


@pytest.fixture
def pack(tmp_path: Path, stocked: Path) -> Path:
    """The whole library, exported."""
    destination = tmp_path / "library.practicepack"
    write_pack(
        destination,
        content_root=stocked,
        exercises=FilesystemContentRepository(stocked).list_exercises(),
    )
    return destination


def rebuilt(source: Path, destination: Path, changes: dict[str, bytes | None]) -> Path:
    """A copy of `source` with entries replaced or removed. Returns `destination`.

    Every failure test below is "a pack that is wrong in one specific way", and
    `zipfile` cannot edit an entry in place — so without this helper each of
    them is the same six lines of copying with the one line that matters buried
    in the middle.
    """
    with zipfile.ZipFile(source) as opened:
        entries = {name: opened.read(name) for name in opened.namelist()}
    for name, body in changes.items():
        if body is None:
            entries.pop(name, None)
        else:
            entries[name] = body
    with zipfile.ZipFile(destination, "w") as target:
        for name in sorted(entries):
            target.writestr(name, entries[name])
    return destination


# --- the port --------------------------------------------------------------


def test_it_satisfies_the_content_repository_port(pack: Path) -> None:
    """Structural, not nominal, exactly as the filesystem repository is.

    This is the assertion PLAN.md §13 asks for: the port now has two real
    implementations rather than one and a fake.
    """
    repository: ContentRepository = PackContentRepository(pack)

    assert len(repository.list_exercises()) == 3


def test_nothing_is_extracted(pack: Path, tmp_path: Path) -> None:
    """The point of the implementation, stated as a test.

    A repository that unpacked to a temporary directory and delegated would be
    an abstraction forwarding one call unchanged, and would prove only that
    `extractall` works.
    """
    before = sorted(path.name for path in tmp_path.iterdir())

    PackContentRepository(pack).list_exercises()

    assert sorted(path.name for path in tmp_path.iterdir()) == before


# --- conformance between the two real implementations ----------------------


def test_both_list_the_same_exercises_in_the_same_order(
    stocked: Path, pack: Path
) -> None:
    """One library, two sources, one answer. The claim a pack is for."""
    on_disk = FilesystemContentRepository(stocked)
    packed = PackContentRepository(pack)

    assert [str(found.id) for found in packed.list_exercises()] == [
        str(found.id) for found in on_disk.list_exercises()
    ]


def test_both_build_identical_aggregates(stocked: Path, pack: Path) -> None:
    """Not just the ids: the whole `Exercise`, spec, hints, notes and all.

    `Exercise` is a frozen dataclass the whole way down, so equality here
    compares every field of every check of every spec — which is what makes
    this one assertion the conformance suite rather than twenty.
    """
    on_disk = FilesystemContentRepository(stocked)
    packed = PackContentRepository(pack)

    assert list(packed.list_exercises()) == list(on_disk.list_exercises())


def test_both_resolve_get_the_same_way(stocked: Path, pack: Path) -> None:
    on_disk = FilesystemContentRepository(stocked)
    packed = PackContentRepository(pack)
    wanted = ExerciseId("katas/two-sum")

    assert packed.get(wanted) == on_disk.get(wanted)


def test_both_return_none_for_an_exercise_that_is_not_there(
    stocked: Path, pack: Path
) -> None:
    missing = ExerciseId("katas/nope")

    assert PackContentRepository(pack).get(missing) is None
    assert FilesystemContentRepository(stocked).get(missing) is None


@pytest.mark.parametrize(
    "criteria",
    [
        pytest.param(ExerciseFilter(), id="everything"),
        pytest.param(
            ExerciseFilter(kinds=frozenset({ExerciseKind.KATA})), id="one-kind"
        ),
        pytest.param(
            ExerciseFilter(kinds=frozenset({ExerciseKind.SQL_DRILL})), id="drills"
        ),
        pytest.param(
            ExerciseFilter(difficulties=frozenset({Difficulty.EASY})), id="difficulty"
        ),
        pytest.param(
            ExerciseFilter(kinds=frozenset({ExerciseKind.GIT_SCENARIO})),
            id="scenarios",
        ),
    ],
)
def test_both_filter_identically(
    stocked: Path, pack: Path, criteria: ExerciseFilter
) -> None:
    """Because both delegate to `ExerciseFilter.matches`, which is in the domain.

    The drift this rules out is the one that makes a second implementation
    worthless: two repositories that each decide for themselves what a filter
    means, agreeing until the day they do not.
    """
    on_disk = FilesystemContentRepository(stocked).list_exercises(criteria)
    packed = PackContentRepository(pack).list_exercises(criteria)

    assert [str(found.id) for found in packed] == [str(found.id) for found in on_disk]


# --- a subset pack is its own library --------------------------------------


def test_a_subset_pack_lists_only_what_it_holds(tmp_path: Path, stocked: Path) -> None:
    """And in the source library's relative order, which the narrowing keeps."""
    on_disk = FilesystemContentRepository(stocked)
    katas = on_disk.list_exercises(ExerciseFilter(kinds=frozenset({ExerciseKind.KATA})))
    destination = tmp_path / "katas.practicepack"
    write_pack(destination, content_root=stocked, exercises=katas)

    packed = PackContentRepository(destination).list_exercises()

    assert [str(found.id) for found in packed] == [str(found.id) for found in katas]


# --- what the manifest is and is not for -----------------------------------


def test_the_order_comes_from_the_curriculum_not_the_manifest(
    tmp_path: Path, pack: Path
) -> None:
    """Two orderings in one file is one too many.

    If the repository obeyed the manifest, a packed library and the same pack
    installed to a content root could list differently and nothing would say
    so. Here the manifest is rewritten into the wrong order and the listing is
    unmoved, which is what pins the single mechanism down.
    """
    reordered = rebuilt(
        pack,
        tmp_path / "reordered.practicepack",
        {
            MANIFEST_FILENAME: (
                f"format: {PACK_FORMAT}\n"
                f"created_with: ''\n"
                f"exercises:\n  - sql/customers-with-no-orders\n"
                f"digests:\n  curriculum.yaml: nonsense\n"
            ).encode()
        },
    )

    packed = PackContentRepository(reordered).list_exercises()

    assert len(packed) == 3
    assert str(packed[0].id) == "katas/two-sum"


def test_the_digests_are_not_checked_on_the_way_to_a_listing(
    tmp_path: Path, pack: Path
) -> None:
    """Verification reads and hashes every file, which is `--check`'s job.

    Doing it on every listing would make opening the library cost a full pass
    over the archive, and it is the same division `loader` and `validation`
    draw: this answers what is in here, and whether it arrived intact is a
    different question with its own command.
    """
    broken = rebuilt(
        pack,
        tmp_path / "broken.practicepack",
        {"katas/two-sum/notes.md": b"edited after the digest was taken"},
    )

    found = PackContentRepository(broken).get(ExerciseId("katas/two-sum"))

    assert found is not None
    assert found.notes == "edited after the digest was taken"


def test_the_manifest_is_still_readable_through_the_repository(pack: Path) -> None:
    """`practice pack --check` needs it, and holds a repository already."""
    assert PackContentRepository(pack).manifest().format == PACK_FORMAT


# --- failures name the file inside the pack --------------------------------


def test_a_pack_with_no_curriculum_is_refused(tmp_path: Path, pack: Path) -> None:
    """A fallback to id order is the accident `curriculum.py` exists to remove."""
    without = rebuilt(
        pack, tmp_path / "without.practicepack", {"curriculum.yaml": None}
    )

    with pytest.raises(ContentError) as caught:
        PackContentRepository(without).list_exercises()

    assert caught.value.problems == ("no such file in the pack",)
    assert str(caught.value.path) == "without.practicepack!curriculum.yaml"


def test_a_pack_missing_an_exercise_it_lists_names_it(
    tmp_path: Path, pack: Path
) -> None:
    """The curriculum promises an exercise the archive does not hold.

    `verify_pack` would call this a missing file; the repository calls it a
    missing file *in the pack*, with the location spelled the way the module
    docstring promises.
    """
    without = rebuilt(
        pack,
        tmp_path / "without.practicepack",
        {"katas/two-sum/exercise.yaml": None},
    )

    with pytest.raises(ContentError) as caught:
        PackContentRepository(without).list_exercises()

    assert str(caught.value.path) == (
        "without.practicepack!katas/two-sum/exercise.yaml"
    )


def test_an_exercise_whose_id_disagrees_with_its_place_is_refused(
    tmp_path: Path, pack: Path
) -> None:
    """The one claim `build_exercise` carries, enforced on this side too.

    Without it a pack could smuggle in an exercise whose `id:` says one thing
    and whose directory says another, which is the disagreement PLAN.md §4.1
    makes impossible on disk by making the id *be* the path.
    """
    with zipfile.ZipFile(pack) as opened:
        document = opened.read("katas/two-sum/exercise.yaml")
    swapped = rebuilt(
        pack,
        tmp_path / "swapped.practicepack",
        {
            "katas/two-sum/exercise.yaml": document.replace(
                b"id: katas/two-sum", b"id: katas/three-sum"
            )
        },
    )

    with pytest.raises(ContentError) as caught:
        PackContentRepository(swapped).list_exercises()

    assert any("does not match" in problem for problem in caught.value.problems)


def test_an_exercise_with_no_notes_is_loaded_rather_than_refused(
    tmp_path: Path, pack: Path
) -> None:
    """Missing notes are a quality rule, not a load failure (PLAN.md §4.2).

    The same call `read_notes` makes on disk, so that `practice validate` is the
    thing with an opinion about it on both sides.
    """
    without = rebuilt(
        pack, tmp_path / "without.practicepack", {"katas/two-sum/notes.md": None}
    )

    found = PackContentRepository(without).get(ExerciseId("katas/two-sum"))

    assert found is not None
    assert found.notes == ""
