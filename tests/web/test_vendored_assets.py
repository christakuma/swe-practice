"""The committed assets are the bytes the manifest says they are.

The offline claim of PLAN.md §8.2 has two halves, and this is the one a grep
cannot make. Our own templates and stylesheets are checked by
`test_offline.py`, which refuses a remote URL in anything we wrote; these four
files we did not write, and a minified library carries its own licence URL in a
banner comment — so grepping them would either condemn an asset that fetches
nothing or be weakened until it caught nothing at all.

Pinning the bytes is the stronger statement in any case. The grep says *this
file names no remote host*; the hash says *this file is the one that was
reviewed*, which is also the only form of the claim that survives someone
dropping a newer, friendlier-looking copy into the directory.

**No network here.** `tools/vendor_assets.py` is what downloads, and it is
outside the package precisely so nothing in the test suite or the shipped wheel
can reach the internet. This reads what is committed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from practice.interface.web.vendor import (
    ASSETS,
    HTMX_VERSION,
    MONACO_LANGUAGES,
    MONACO_VERSION,
    TREES,
    VENDOR_DIRNAME,
    VendoredAsset,
    digest,
    editor_language,
    local_name,
    pinned_paths,
    static_root,
    tree_digest,
    verify,
)

if TYPE_CHECKING:
    from pathlib import Path


def test_every_vendored_asset_matches_its_pinned_hash() -> None:
    assert verify() == ()


def test_the_manifest_is_not_empty() -> None:
    """So the assertion above cannot pass by there being nothing to check.

    The same shape of guard the architecture test puts on its own walk: a
    verification that iterates an empty list is green forever while checking
    nothing.

    A literal count rather than `> 0`, so adding an asset is a deliberate edit
    here. One file and one tree since Phase 27, which replaced CodeMirror's
    eight files with Monaco pinned as a directory (ADR 0034).
    """
    assert len(ASSETS) == 1
    assert len(TREES) == 1
    assert all(asset.sha256 for asset in ASSETS)
    assert all(tree.sha256 and tree.members for tree in TREES)


def test_every_asset_lives_under_the_vendor_directory() -> None:
    """Which is what lets the offline grep decide what it is skipping.

    `test_offline.py` excludes `static/vendor/` by this constant. An asset
    committed anywhere else under `static/` would be covered by neither rule, so
    the manifest is held to the convention rather than trusted to follow it.
    """
    assert all(asset.path.startswith(f"{VENDOR_DIRNAME}/") for asset in ASSETS)
    assert all(tree.path.startswith(f"{VENDOR_DIRNAME}/") for tree in TREES)


def test_the_pinned_versions_are_the_ones_the_files_report() -> None:
    """A hash check cannot tell you that you pinned the hash of the wrong version.

    Both libraries carry their version as a literal in their own source, so the
    two statements -- the number in the manifest and the number in the bytes --
    can be compared. Worth doing because the failure it catches is the plausible
    one: a version bumped in `vendor.py` and a hash pasted from the run before.
    """
    static = static_root()
    htmx = (static / VENDOR_DIRNAME / "htmx.min.js").read_text(encoding="utf-8")
    monaco = static / VENDOR_DIRNAME / "monaco" / "vs" / "editor" / "editor.main.js"

    assert f'version:"{HTMX_VERSION}"' in htmx
    assert f"Version: {MONACO_VERSION}(" in monaco.read_text(encoding="utf-8")


def test_no_codemirror_file_remains() -> None:
    """ADR 0034 supersedes ADR 0010, and "two engines" is the state to refuse.

    The manifest no longer names one, and `test_every_file_is_covered_by_one_of_
    the_two_rules` would already fail an unpinned straggler -- this says it in the
    words the exit criterion uses, so deleting the line above cannot hide it.
    """
    stragglers = [
        path.name
        for path in (static_root() / VENDOR_DIRNAME).rglob("*")
        if "codemirror" in path.name.lower()
    ]

    assert stragglers == []


def test_the_urls_are_https_and_name_the_pinned_version() -> None:
    """The record of where a byte came from is only useful if it is specific.

    A `latest` URL would make the manifest unable to say what it holds, and the
    next download would quietly fetch something else.
    """
    for asset in ASSETS:
        assert asset.url.startswith("https://"), asset.path
        assert HTMX_VERSION in asset.url, asset.path
    for tree in TREES:
        assert tree.url.startswith("https://"), tree.path
        assert MONACO_VERSION in tree.url, tree.path


def test_a_tree_is_pinned_as_the_directory_it_is() -> None:
    """Every kept file is on disk, the hash covers them, and nothing else is there."""
    tree = TREES[0]
    base = tree.location(static_root())
    on_disk = {
        path.relative_to(base).as_posix(): path.read_bytes()
        for path in base.rglob("*")
        if path.is_file()
    }

    assert set(on_disk) == {local_name(member) for member in tree.members}
    assert tree_digest(on_disk) == tree.sha256


def test_a_tree_hash_notices_a_rename_and_a_byte() -> None:
    """The detector's own properties: content, name, and where a boundary falls."""
    base = tree_digest({"a.js": b"x", "b.js": b"y"})

    assert tree_digest({"a.js": b"x", "b.js": b"z"}) != base
    assert tree_digest({"a.js": b"x", "c.js": b"y"}) != base
    assert tree_digest({"a.js": b"xy", "b.js": b""}) != base
    assert tree_digest({"b.js": b"y", "a.js": b"x"}) == base


def test_a_tree_with_a_stray_or_a_tampered_file_is_reported(tmp_path: Path) -> None:
    """Both halves: a file nobody pinned, and a pinned file that changed."""
    tree = TREES[0]
    _copy_vendor(tmp_path)
    target = tree.location(tmp_path)
    assert verify(tmp_path) == ()

    (target / "vs" / "stray.js").write_bytes(b"1")
    assert [p for p in verify(tmp_path) if "stray.js" in p]

    (target / "vs" / "stray.js").unlink()
    (target / "vs" / "loader.js").write_bytes(b"alert(1)")
    problems = verify(tmp_path)
    assert len(problems) == 1
    assert tree.path in problems[0]


def _copy_vendor(destination: Path) -> None:
    """The real `vendor/` directory, copied, so a test can break one thing in it."""
    source = static_root() / VENDOR_DIRNAME
    for path in source.rglob("*"):
        if path.is_file():
            copy = destination / VENDOR_DIRNAME / path.relative_to(source)
            copy.parent.mkdir(parents=True, exist_ok=True)
            copy.write_bytes(path.read_bytes())


def test_a_tampered_asset_is_reported(tmp_path: Path) -> None:
    """The detector itself, because a verifier that cannot fail proves nothing."""
    asset = ASSETS[0]
    _copy_vendor(tmp_path)
    asset.location(tmp_path).write_bytes(b"alert('hello from somewhere else')")

    problems = verify(tmp_path)

    assert len(problems) == 1
    assert asset.path in problems[0]
    assert asset.sha256 in problems[0]


def test_a_missing_asset_is_reported_as_missing(tmp_path: Path) -> None:
    """A distinct message, because the fix is distinct: run the downloader."""
    problems = verify(tmp_path)

    assert len(problems) == len(ASSETS) + len(TREES[0].members)
    assert all("is missing" in problem for problem in problems)


def test_an_unpinned_asset_cannot_pass_by_hashing_to_nothing(tmp_path: Path) -> None:
    """An empty `sha256` is the first-run state, and it must not be a pass.

    The downloader exits non-zero until a human pins what arrived; this is the
    half of that rule which holds even if someone commits the empty string.
    """
    unpinned = VendoredAsset(
        path=f"{VENDOR_DIRNAME}/x.js", url="https://x/x.js", sha256=""
    )
    location = unpinned.location(tmp_path)
    location.parent.mkdir(parents=True)
    location.write_bytes(b"")

    assert digest(b"") != unpinned.sha256


@pytest.mark.parametrize("path", sorted(pinned_paths()))
def test_each_asset_is_checked_out_with_unix_line_endings(path: str) -> None:
    """`.gitattributes` marks these `-text`, and this is why it has to.

    The hash is over the downloaded bytes, and those use LF. Git's `text=auto`
    would normalize them to CRLF on a Windows checkout, which changes every hash
    and makes the check above fail on one platform and pass on the other -- the
    same cross-platform trap `content/fixtures.lock` exists to catch.
    """
    payload = (static_root() / path).read_bytes()

    if not path.endswith(".ttf"):  # a font is binary; any byte pair is allowed
        assert b"\r\n" not in payload


def test_a_language_nobody_vendored_is_none_not_an_error() -> None:
    """`None` for both, which the template renders as an editor with no colour.

    A scenario has no language at all and a made-up one has no tokenizer; the
    same branch serves both, and neither can be the reason a page 500s.
    """
    assert editor_language(None) is None
    assert editor_language("cobol") is None


def test_every_kata_language_has_a_tokenizer() -> None:
    assert {editor_language(name) for name in MONACO_LANGUAGES} == MONACO_LANGUAGES
    basic = static_root() / VENDOR_DIRNAME / "monaco" / "vs" / "basic-languages"
    assert {path.name for path in basic.iterdir()} == MONACO_LANGUAGES


def test_every_pinned_path_exists() -> None:
    root = static_root()

    assert all((root / path).is_file() for path in pinned_paths())
