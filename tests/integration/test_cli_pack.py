"""`practice pack`, driven through Typer's runner.

Integration for the reason `test_cli_validate.py` is: the command's whole job is
to turn a directory into a file and back, and the exit code is the contract — a
test that stubbed the filesystem would verify neither.

**The claim this file carries that no other test can** is that each of the three
modes is *reachable*. ADR 0018's lesson, now applied for the third time: a
format nobody can write and a pack nobody can install are written rather than
shipped, and every other test in Phase 16 calls the functions directly.
"""

from __future__ import annotations

import hashlib
import re
import zipfile
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from practice.adapters.content.pack import MANIFEST_FILENAME
from practice.interface.cli.main import app

from .conftest import a_drill, a_kata, a_scenario

if TYPE_CHECKING:
    from pathlib import Path

    from .conftest import WriteExercise

runner = CliRunner()


def run(*arguments: str) -> tuple[int, str]:
    result = runner.invoke(app, ["pack", *arguments])
    return result.exit_code, result.output


@pytest.fixture
def stocked(library: Path, write_exercise: WriteExercise) -> Path:
    write_exercise(a_kata())
    write_exercise(a_scenario())
    write_exercise(a_drill())
    return library


# --- export ----------------------------------------------------------------


def test_exporting_writes_a_pack_and_names_what_went_in(
    tmp_path: Path, stocked: Path
) -> None:
    destination = tmp_path / "out.practicepack"

    code, output = run("--out", str(destination), "--content-root", str(stocked))

    assert code == 0, output
    assert destination.is_file()
    assert "katas/two-sum" in output
    assert "3 exercises and" in output


def test_exporting_says_how_to_install_what_it_just_wrote(
    tmp_path: Path, stocked: Path
) -> None:
    """The next step, in the output, because a pack on disk does nothing.

    The same reason `fixtures --check` prints how to regenerate and `start`
    prints what to run next: a tool that produces an artifact and goes quiet
    leaves the user to guess.
    """
    destination = tmp_path / "out.practicepack"

    _, output = run("--out", str(destination), "--content-root", str(stocked))

    assert "--install" in output
    assert "--into" in output


def test_a_kind_filter_exports_only_that_kind(tmp_path: Path, stocked: Path) -> None:
    destination = tmp_path / "out.practicepack"

    code, output = run(
        "--out",
        str(destination),
        "--content-root",
        str(stocked),
        "--kind",
        "kata",
    )

    assert code == 0, output
    assert "katas/two-sum" in output
    assert "git/undo-a-commit" not in output
    assert "1 exercise and" in output


def test_a_difficulty_filter_is_honoured_too(tmp_path: Path, stocked: Path) -> None:
    """Both filter dimensions reach `ExerciseFilter`, which does the matching."""
    code, output = run(
        "--out",
        str(tmp_path / "out.practicepack"),
        "--content-root",
        str(stocked),
        "--difficulty",
        "hard",
    )

    assert code == 1, output
    assert "at least one exercise" in output


def test_a_filter_that_selects_nothing_is_refused_rather_than_written(
    tmp_path: Path, stocked: Path
) -> None:
    """A pack of nothing installs to a library `validate` calls empty, later.

    Exit 1 and no file, so a scripted export cannot quietly produce one.
    """
    destination = tmp_path / "out.practicepack"

    code, _ = run(
        "--out",
        str(destination),
        "--content-root",
        str(stocked),
        "--kind",
        "kata",
        "--difficulty",
        "hard",
    )

    assert code == 1
    assert not destination.exists()


def test_an_unknown_kind_is_rejected_by_the_parser(
    tmp_path: Path, stocked: Path
) -> None:
    """Typer validates it against the enum, so the error names the choices."""
    code, _ = run(
        "--out",
        str(tmp_path / "out.practicepack"),
        "--content-root",
        str(stocked),
        "--kind",
        "shell_drill",
    )

    assert code == 2


# --- check -----------------------------------------------------------------


def test_checking_a_good_pack_lists_it_and_exits_zero(
    tmp_path: Path, stocked: Path
) -> None:
    destination = tmp_path / "out.practicepack"
    run("--out", str(destination), "--content-root", str(stocked))

    code, output = run("--check", str(destination))

    assert code == 0, output
    assert "all matching" in output
    assert "katas/two-sum" in output


def test_checking_names_the_version_that_wrote_the_pack(
    tmp_path: Path, stocked: Path
) -> None:
    """Provenance, and the reason the manifest carries it.

    A pack is a file somebody keeps; "which `practice` made this" is the first
    question when it will not open.
    """
    destination = tmp_path / "out.practicepack"
    run("--out", str(destination), "--content-root", str(stocked))

    _, output = run("--check", str(destination))

    assert "Written by" in output


def test_checking_a_damaged_pack_fails_and_says_what_moved(
    tmp_path: Path, stocked: Path
) -> None:
    destination = tmp_path / "out.practicepack"
    run("--out", str(destination), "--content-root", str(stocked))
    _edit(destination, "katas/two-sum/notes.md", b"damaged in transit")

    code, output = run("--check", str(destination))

    assert code == 1
    assert "katas/two-sum/notes.md" in output
    assert "digest is" in output


def test_checking_a_damaged_pack_says_what_to_do_about_it(
    tmp_path: Path, stocked: Path
) -> None:
    """And is careful about what it claims.

    The digests catch corruption; they cannot distinguish it from an edit,
    because a pack is not signed and anyone who can change a file can change
    its digest. So the advice is "fetch it again" rather than an accusation.
    """
    destination = tmp_path / "out.practicepack"
    run("--out", str(destination), "--content-root", str(stocked))
    _edit(destination, "katas/two-sum/notes.md", b"damaged in transit")

    _, output = run("--check", str(destination))

    assert "fetch it again" in output


def test_checking_something_that_is_not_a_zip_says_so(tmp_path: Path) -> None:
    rubbish = tmp_path / "out.practicepack"
    rubbish.write_bytes(b"not a zip at all")

    code, output = run("--check", str(rubbish))

    assert code == 1
    assert "cannot be read as a zip" in output


def test_checking_a_pack_that_is_not_there_says_so(tmp_path: Path) -> None:
    code, output = run("--check", str(tmp_path / "nope.practicepack"))

    assert code == 1
    assert "no such file" in output


def test_a_pack_whose_digests_match_and_whose_library_is_broken_is_distinguished(
    tmp_path: Path, stocked: Path
) -> None:
    """The two claims `--check` makes, told apart in the output.

    A pack can be a perfectly intact archive of a library that will not load.
    Reporting that as a digest failure would send somebody to re-download a
    file that arrived exactly as it was sent.
    """
    destination = tmp_path / "out.practicepack"
    run("--out", str(destination), "--content-root", str(stocked))
    _edit(destination, "curriculum.yaml", b"tracks: nonsense\n", rehash=True)

    code, output = run("--check", str(destination))

    assert code == 1
    assert "every file matches its digest" in output


# --- install ---------------------------------------------------------------


def test_installing_lays_out_a_content_root(tmp_path: Path, stocked: Path) -> None:
    destination = tmp_path / "out.practicepack"
    run("--out", str(destination), "--content-root", str(stocked))
    into = tmp_path / "installed"

    code, output = run("--install", str(destination), "--into", str(into))

    assert code == 0, output
    assert (into / "curriculum.yaml").is_file()
    assert (into / "katas" / "two-sum" / "exercise.yaml").is_file()
    assert "3 exercises installed" in output


def test_installing_says_how_to_use_what_it_installed(
    tmp_path: Path, stocked: Path
) -> None:
    """`--content-root` is how an installed library is reached, and it is not
    guessable from the fact that a directory now exists.
    """
    destination = tmp_path / "out.practicepack"
    run("--out", str(destination), "--content-root", str(stocked))

    _, output = run(
        "--install", str(destination), "--into", str(tmp_path / "installed")
    )

    assert "practice validate --content-root" in output
    assert "practice up --content-root" in output


def test_installing_without_a_destination_is_refused(
    tmp_path: Path, stocked: Path
) -> None:
    """Guessing where to write several hundred files is the one thing it must
    not do, so `--into` is required rather than defaulted.
    """
    destination = tmp_path / "out.practicepack"
    run("--out", str(destination), "--content-root", str(stocked))

    code, output = run("--install", str(destination))

    assert code == 2
    assert "--into" in output


def test_installing_into_an_occupied_directory_is_refused(
    tmp_path: Path, stocked: Path
) -> None:
    """Two libraries in one root is a root where neither validates.

    `curriculum.yaml` names one library's exercises and the walk finds both, so
    `validate_library` reports every exercise of the other as unlisted.
    """
    destination = tmp_path / "out.practicepack"
    run("--out", str(destination), "--content-root", str(stocked))
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "something").write_text("here first", encoding="utf-8")

    code, output = run("--install", str(destination), "--into", str(occupied))

    assert code == 2
    assert "not empty" in output


def test_a_damaged_pack_installs_nothing(tmp_path: Path, stocked: Path) -> None:
    """Half a library looks like a library, and the next command run against it
    reports a missing exercise rather than a bad download.
    """
    destination = tmp_path / "out.practicepack"
    run("--out", str(destination), "--content-root", str(stocked))
    _edit(destination, "katas/two-sum/notes.md", b"damaged")
    into = tmp_path / "installed"

    code, _ = run("--install", str(destination), "--into", str(into))

    assert code == 1
    assert not into.exists()


# --- the modes are exclusive ----------------------------------------------


def test_checking_and_installing_at_once_is_refused(
    tmp_path: Path, stocked: Path
) -> None:
    """Two destinations and one subject. Better to ask than to pick one."""
    destination = tmp_path / "out.practicepack"
    run("--out", str(destination), "--content-root", str(stocked))

    code, output = run("--check", str(destination), "--install", str(destination))

    assert code == 2
    assert "one at a time" in output


def _edit(destination: Path, member: str, body: bytes, *, rehash: bool = False) -> None:
    """Rewrite one entry of a pack, optionally fixing its digest to match.

    `rehash=False` is the corrupt-in-transit case the digests are for.
    `rehash=True` is the rarer and more interesting one: an archive that is
    exactly what its manifest says it is, holding a library that will not load.
    """
    with zipfile.ZipFile(destination) as opened:
        entries = {name: opened.read(name) for name in opened.namelist()}
    entries[member] = body
    if rehash:
        manifest = entries[MANIFEST_FILENAME].decode("utf-8")
        entries[MANIFEST_FILENAME] = re.sub(
            rf"(?m)^(  {re.escape(member)}: ).*$",
            rf"\g<1>{hashlib.sha256(body).hexdigest()}",
            manifest,
        ).encode()
    with zipfile.ZipFile(destination, "w") as target:
        for name in sorted(entries):
            target.writestr(name, entries[name])
