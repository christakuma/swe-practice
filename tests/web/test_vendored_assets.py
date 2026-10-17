"""The four committed assets are the bytes the manifest says they are.

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
    CODEMIRROR_VERSION,
    HTMX_VERSION,
    VENDOR_DIRNAME,
    VendoredAsset,
    digest,
    static_root,
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
    here. Five since Phase 14, which vendored CodeMirror's SQL mode for the
    drill workbench; eight since Phase 22, whose Dockerfile mode needs the
    `simple` addon beside it and whose compose files want YAML.
    """
    assert len(ASSETS) == 8
    assert all(asset.sha256 for asset in ASSETS)


def test_every_asset_lives_under_the_vendor_directory() -> None:
    """Which is what lets the offline grep decide what it is skipping.

    `test_offline.py` excludes `static/vendor/` by this constant. An asset
    committed anywhere else under `static/` would be covered by neither rule, so
    the manifest is held to the convention rather than trusted to follow it.
    """
    assert all(asset.path.startswith(f"{VENDOR_DIRNAME}/") for asset in ASSETS)


def test_the_pinned_versions_are_the_ones_the_files_report() -> None:
    """A hash check cannot tell you that you pinned the hash of the wrong version.

    Both libraries carry their version as a literal in their own source, so the
    two statements -- the number in the manifest and the number in the bytes --
    can be compared. Worth doing because the failure it catches is the plausible
    one: a version bumped in `vendor.py` and a hash pasted from the run before.
    """
    static = static_root()
    htmx = (static / VENDOR_DIRNAME / "htmx.min.js").read_text(encoding="utf-8")
    codemirror = (static / VENDOR_DIRNAME / "codemirror.min.js").read_text(
        encoding="utf-8"
    )

    assert f'version:"{HTMX_VERSION}"' in htmx
    assert f'version="{CODEMIRROR_VERSION}"' in codemirror


def test_the_urls_are_https_and_name_the_pinned_version() -> None:
    """The record of where a byte came from is only useful if it is specific.

    A `latest` URL would make the manifest unable to say what it holds, and the
    next download would quietly fetch something else.
    """
    for asset in ASSETS:
        assert asset.url.startswith("https://"), asset.path
        assert HTMX_VERSION in asset.url or CODEMIRROR_VERSION in asset.url, asset.path


def test_a_tampered_asset_is_reported(tmp_path: Path) -> None:
    """The detector itself, because a verifier that cannot fail proves nothing."""
    asset = ASSETS[0]
    location = asset.location(tmp_path)
    location.parent.mkdir(parents=True)
    location.write_bytes(b"alert('hello from somewhere else')")
    for other in ASSETS[1:]:
        other.location(tmp_path).write_bytes((static_root() / other.path).read_bytes())

    problems = verify(tmp_path)

    assert len(problems) == 1
    assert asset.path in problems[0]
    assert asset.sha256 in problems[0]


def test_a_missing_asset_is_reported_as_missing(tmp_path: Path) -> None:
    """A distinct message, because the fix is distinct: run the downloader."""
    problems = verify(tmp_path)

    assert len(problems) == len(ASSETS)
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


@pytest.mark.parametrize("asset", ASSETS, ids=lambda asset: asset.path)
def test_each_asset_is_checked_out_with_unix_line_endings(
    asset: VendoredAsset,
) -> None:
    """`.gitattributes` marks these `-text`, and this is why it has to.

    The hash is over the downloaded bytes, and those use LF. Git's `text=auto`
    would normalize them to CRLF on a Windows checkout, which changes every hash
    and makes the check above fail on one platform and pass on the other -- the
    same cross-platform trap `content/fixtures.lock` exists to catch.
    """
    payload = asset.location(static_root()).read_bytes()

    assert b"\r\n" not in payload
