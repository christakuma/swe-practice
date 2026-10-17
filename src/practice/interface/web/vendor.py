"""The third-party assets this app ships, pinned by version and by hash.

Offline means vendoring everything, with no CDN links at all (PLAN.md §8.2). The
files themselves are committed; what lives here is the record of *which* bytes
they are supposed to be, which is the part a reader cannot reconstruct from the
directory listing.

**The manifest is in the package rather than in the download script**, which is
the one decision in this module. Two callers need it and only one of them is the
downloader: `tools/vendor_assets.py` fetches, and `tests/web/` verifies what is
on disk against the same list. A manifest inside the script would make the
verification test import a tool that is not shipped, and a second copy of the
hashes would drift the first time a version moved.

**Why a hash check instead of grepping the vendored files.** The offline-asset
test greps our own templates and stylesheets for `http://` and `//cdn`, and it
deliberately does *not* grep these four: a minified library carries its own
licence URL in a banner comment, so the grep would either fail on an asset that
fetches nothing or have to be weakened until it caught nothing. Pinned bytes are
the stronger statement anyway — the grep says "this file names no remote host",
and the hash says "this file is the one that was reviewed".

Upgrading one is two steps: change the version and the hash here, then run
`uv run python tools/vendor_assets.py`. The test fails in between, which is the
point of doing it in that order.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

__all__ = [
    "ASSETS",
    "CODEMIRROR_VERSION",
    "HTMX_VERSION",
    "VENDOR_DIRNAME",
    "VendoredAsset",
    "digest",
    "mode_files",
    "static_root",
    "verify",
]

#: Pinned, not tracked. htmx 2 is the line whose attribute vocabulary this app's
#: templates are written against; a major upgrade is a template change and should
#: read as one in the diff rather than arriving with a hash bump.
HTMX_VERSION: Final = "2.0.11"

#: CodeMirror **5**, not 6, and the tradeoff is recorded in ADR 0010: CM6 is ESM
#: and needs a bundler, which would drag an npm toolchain into a Python project
#: for one textarea. CM5 is in maintenance mode and drops in as three files.
CODEMIRROR_VERSION: Final = "5.65.21"

#: Everything under `static/` with this name is third party and hash-pinned. The
#: offline-asset grep uses the same constant to decide what it is *not* grepping,
#: so the two rules cannot disagree about which files they cover.
VENDOR_DIRNAME: Final = "vendor"


@dataclass(frozen=True, slots=True)
class VendoredAsset:
    """One committed file, where it came from, and what it must hash to."""

    path: str
    url: str
    sha256: str

    def location(self, static: Path) -> Path:
        """Where this asset sits under a `static/` directory."""
        return static.joinpath(*self.path.split("/"))


ASSETS: Final[tuple[VendoredAsset, ...]] = (
    VendoredAsset(
        path=f"{VENDOR_DIRNAME}/htmx.min.js",
        url=(f"https://cdnjs.cloudflare.com/ajax/libs/htmx/{HTMX_VERSION}/htmx.min.js"),
        sha256="d6fdc75f204e6bdefa99b69bf1e6d4ac69b8a364f77929f45c13476b4000f717",
    ),
    VendoredAsset(
        path=f"{VENDOR_DIRNAME}/codemirror.min.js",
        url=(
            f"https://cdnjs.cloudflare.com/ajax/libs/codemirror/{CODEMIRROR_VERSION}"
            f"/codemirror.min.js"
        ),
        sha256="d649a8d6bd5d0ca9bb3bef8212c9de6fa5599af3e3fe2898f94861dfe87bea7d",
    ),
    VendoredAsset(
        path=f"{VENDOR_DIRNAME}/codemirror.min.css",
        url=(
            f"https://cdnjs.cloudflare.com/ajax/libs/codemirror/{CODEMIRROR_VERSION}"
            f"/codemirror.min.css"
        ),
        sha256="22f18b4dec95cc981a96f8e69f61f595314162fd102ba401abcd20b0674d9846",
    ),
    # The language modes, flattened out of the library's own `mode/<name>/`
    # nesting. PLAN.md §15 Q3 asked what a second language costs, and this file
    # answered "a second line here and nothing else".
    #
    # **Phase 14 tested that and it was nearly right.** Adding SQL is one line
    # here, one file committed beside the others, and no change to `verify`, the
    # offline grep, the asset route or the hash test. What it is *not* is
    # nothing else: `workbench.html` had `codemirror-python.min.js` written into
    # the script tag, so the page served a Python tokenizer and then asked
    # CodeMirror for a `sql` mode it had not loaded — which fails by silently
    # giving you a plain textarea, the worst available way for it to fail.
    #
    # The fix is that the template builds the filename from `editor_mode`, which
    # is why `_MODE_FILES` below exists: the set of modes that have a file is a
    # fact about this manifest, so the one place that knows it is this module
    # rather than a template guessing at a path.
    VendoredAsset(
        path=f"{VENDOR_DIRNAME}/codemirror-python.min.js",
        url=(
            f"https://cdnjs.cloudflare.com/ajax/libs/codemirror/{CODEMIRROR_VERSION}"
            f"/mode/python/python.min.js"
        ),
        sha256="d545dba0fd28b288f13383440a8f763228bc38cbf987d28ee870e4baa1438b21",
    ),
    VendoredAsset(
        path=f"{VENDOR_DIRNAME}/codemirror-sql.min.js",
        url=(
            f"https://cdnjs.cloudflare.com/ajax/libs/codemirror/{CODEMIRROR_VERSION}"
            f"/mode/sql/sql.min.js"
        ),
        sha256="4c89a2e950b4c627d7ace5642495f815d5c3cf26302eeaaa92882636d5026af6",
    ),
    # Phase 22: the fourth kind's two languages. The Dockerfile mode is built
    # on CodeMirror's `simple` mode addon, so it is two files where every mode
    # before it was one -- which is why `mode_files` returns a tuple.
    VendoredAsset(
        path=f"{VENDOR_DIRNAME}/codemirror-simple.min.js",
        url=(
            f"https://cdnjs.cloudflare.com/ajax/libs/codemirror/{CODEMIRROR_VERSION}"
            f"/addon/mode/simple.min.js"
        ),
        sha256="cc4e091d53fe943388368929cbd74d68e5bb3883695c177ee91347d03d0f8e1a",
    ),
    VendoredAsset(
        path=f"{VENDOR_DIRNAME}/codemirror-dockerfile.min.js",
        url=(
            f"https://cdnjs.cloudflare.com/ajax/libs/codemirror/{CODEMIRROR_VERSION}"
            f"/mode/dockerfile/dockerfile.min.js"
        ),
        sha256="0e6d1f15568767ec4ae4f48e101f3065e86bc5cc29a6893853018e92d8eac967",
    ),
    VendoredAsset(
        path=f"{VENDOR_DIRNAME}/codemirror-yaml.min.js",
        url=(
            f"https://cdnjs.cloudflare.com/ajax/libs/codemirror/{CODEMIRROR_VERSION}"
            f"/mode/yaml/yaml.min.js"
        ),
        sha256="502bed0f3a9db7ee6c3dfea6984eab3b0a4c474387621b06a04a3cff92a5c312",
    ),
)

#: CodeMirror mode name to the vendored files that define it, in load order.
#:
#: The template reads this through `mode_files`, rather than interpolating the
#: mode name into a path itself. A missing entry is then a `None` the template
#: can branch on, instead of a 404 on a script tag — and a mode whose file was
#: never vendored degrades to a plain textarea *visibly*, in the one place that
#: can tell the difference.
_MODE_FILES: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "python": (f"{VENDOR_DIRNAME}/codemirror-python.min.js",),
        "sql": (f"{VENDOR_DIRNAME}/codemirror-sql.min.js",),
        # The addon first: the mode file calls `defineSimpleMode` on load.
        "dockerfile": (
            f"{VENDOR_DIRNAME}/codemirror-simple.min.js",
            f"{VENDOR_DIRNAME}/codemirror-dockerfile.min.js",
        ),
        "yaml": (f"{VENDOR_DIRNAME}/codemirror-yaml.min.js",),
    }
)


def mode_files(mode: str | None) -> tuple[str, ...]:
    """The vendored files defining a CodeMirror mode, or `()` if there are none.

    `()` for `None` as well as for an unknown name, so a git scenario — which
    has no editor at all — takes the same branch as a language nobody vendored.
    The template renders no CodeMirror either way, which is correct for both.
    """
    return _MODE_FILES.get(mode, ()) if mode is not None else ()


def static_root() -> Path:
    """The `static/` directory that ships inside this package.

    Derived from `__file__` rather than from the working directory, for the same
    reason `config.project_root` is: the server has to find its own assets from
    wherever it was started.
    """
    return Path(__file__).resolve().parent / "static"


def digest(payload: bytes) -> str:
    """The hash this module records, computed the one way it is computed."""
    return hashlib.sha256(payload).hexdigest()


def verify(static: Path | None = None) -> tuple[str, ...]:
    """Every way the files on disk disagree with this manifest.

    All of them, rather than the first: a version bump that forgot to re-run the
    downloader is four problems, and reporting one at a time would take four runs
    to find that out. The same reason `practice validate` reports a whole library.
    """
    root = static if static is not None else static_root()
    return tuple(_problems(root))


def _problems(root: Path) -> Iterator[str]:
    for asset in ASSETS:
        location = asset.location(root)
        if not location.is_file():
            yield f"{asset.path} is missing; run tools/vendor_assets.py"
            continue
        found = digest(location.read_bytes())
        if found != asset.sha256:
            yield (
                f"{asset.path} hashes to {found}, not the pinned "
                f"{asset.sha256 or '<nothing>'}"
            )
