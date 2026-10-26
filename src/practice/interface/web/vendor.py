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

**Monaco is pinned as a directory** (ADR 0034). It is ten files once
trimmed, and ten rows of near-identical `VendoredAsset`s would bury the one
fact that matters, which is that they were taken together from one release. A
`VendoredTree` records the tarball, the members kept, and *one* hash over the
lot (`tree_digest`: every file's path and content hash, sorted). The
bytes-on-disk-match-the-manifest test keeps its meaning, and a file added to or
missing from the directory fails it, which a per-file list could not see.

Upgrading one is two steps: change the version and the hash here, then run
`uv run python tools/vendor_assets.py`. The test fails in between, which is the
point of doing it in that order.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

__all__ = [
    "ASSETS",
    "HTMX_VERSION",
    "MONACO_LANGUAGES",
    "MONACO_VERSION",
    "TREES",
    "VENDOR_DIRNAME",
    "VendoredAsset",
    "VendoredTree",
    "digest",
    "editor_language",
    "local_name",
    "pinned_paths",
    "static_root",
    "tree_digest",
    "verify",
]

#: Pinned, not tracked. htmx 2 is the line whose attribute vocabulary this app's
#: templates are written against; a major upgrade is a template change and should
#: read as one in the diff rather than arriving with a hash bump.
HTMX_VERSION: Final = "2.0.11"

#: Monaco, the editor VS Code is built on (ADR 0034, which supersedes ADR 0010's
#: CodeMirror 5). **0.52.2 and not newer, on purpose**: later releases ship the
#: ESM-first layout, where `editor.main` statically pulls in a 7 MB TypeScript
#: worker and three others this app has no use for, and trimming a hashed-chunk
#: graph by hand is a fight with the build. 0.52 is the last release with the
#: classic AMD layout, whose language services are separate files that are only
#: fetched when a model asks for that language -- so not vendoring them is a
#: trim and not a repair.
MONACO_VERSION: Final = "0.52.2"

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


@dataclass(frozen=True, slots=True)
class VendoredTree:
    """A directory taken whole from one archive, pinned by one hash.

    `members` are archive paths below the tarball's `package/`; a leading `min/`
    is dropped to get the path under `path`. See the module docstring for why
    this is a second kind of entry and not many `VendoredAsset`s.
    """

    path: str
    url: str
    members: tuple[str, ...]
    sha256: str

    def files(self) -> tuple[str, ...]:
        """Each kept file as a path under `static/`, in manifest order."""
        return tuple(f"{self.path}/{local_name(m)}" for m in self.members)

    def location(self, static: Path) -> Path:
        """The directory this tree occupies under a `static/` directory."""
        return static.joinpath(*self.path.split("/"))


def local_name(member: str) -> str:
    """An archive member's path inside its tree: `min/` is a packaging detail."""
    return member.removeprefix("min/")


ASSETS: Final[tuple[VendoredAsset, ...]] = (
    VendoredAsset(
        path=f"{VENDOR_DIRNAME}/htmx.min.js",
        url=(f"https://cdnjs.cloudflare.com/ajax/libs/htmx/{HTMX_VERSION}/htmx.min.js"),
        sha256="d6fdc75f204e6bdefa99b69bf1e6d4ac69b8a364f77929f45c13476b4000f717",
    ),
)

#: What of Monaco is kept, as archive members relative to the tarball's
#: `package/`. `min/` is stripped on the way to disk, so `min/vs/loader.js`
#: lands at `vendor/monaco/vs/loader.js` and the AMD loader's `paths.vs` is
#: simply `<static>/vendor/monaco/vs`.
#:
#: The core, the four tokenizers a shipped exercise is written in (Python for
#: katas and quiz fixes, SQL for drills, Dockerfile and YAML for the container
#: kind), the one worker file, and the icon font the find widget draws with.
#: Not the CSS/HTML/JSON/TypeScript language services and not the nine
#: `nls.messages.*` translations: nothing here asks for them, and they are most
#: of the 25 MB the full package would add to the wheel.
_MONACO_MEMBERS: Final = (
    "LICENSE",
    "min/vs/loader.js",
    "min/vs/editor/editor.main.js",
    "min/vs/editor/editor.main.css",
    "min/vs/base/worker/workerMain.js",
    "min/vs/base/browser/ui/codicons/codicon/codicon.ttf",
    "min/vs/basic-languages/python/python.js",
    "min/vs/basic-languages/sql/sql.js",
    "min/vs/basic-languages/yaml/yaml.js",
    "min/vs/basic-languages/dockerfile/dockerfile.js",
)

TREES: Final[tuple[VendoredTree, ...]] = (
    VendoredTree(
        path=f"{VENDOR_DIRNAME}/monaco",
        url=(
            f"https://registry.npmjs.org/monaco-editor/-/"
            f"monaco-editor-{MONACO_VERSION}.tgz"
        ),
        members=_MONACO_MEMBERS,
        sha256="0f4fd468ccceb9caa16b8bc643aa096831f718398f7a64e3aecefd8c17b6bd2e",
    ),
)

#: The Monaco language ids this app has a tokenizer for. A kata's
#: `editable.language` is already a Monaco id (`python`, `sql`, `yaml`,
#: `dockerfile`), which is why this is a set and not a translation table.
MONACO_LANGUAGES: Final = frozenset({"python", "sql", "yaml", "dockerfile"})


def editor_language(language: str | None) -> str | None:
    """The Monaco language id for an exercise's language, or `None` for "plain".

    `None` for `None` as well as for a language nobody vendored, so a git
    scenario -- which has no editor -- and a language with no tokenizer take the
    same branch. An editor with no tokenizer is still an editor: a language
    nobody vendored degrades to uncoloured text, which is visible, rather than
    to a textarea, which would be a different widget with different keys.
    """
    return language if language in MONACO_LANGUAGES else None


def pinned_paths() -> frozenset[str]:
    """Every file under `static/` the manifest vouches for, as posix paths."""
    return frozenset(
        [asset.path for asset in ASSETS]
        + [path for tree in TREES for path in tree.files()]
    )


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


def tree_digest(files: Mapping[str, bytes]) -> str:
    """One hash for a directory: each file's path and content hash, sorted.

    Hashing the *list of per-file hashes* and not the concatenated bytes means a
    renamed file changes it and a moved boundary between two files cannot cancel
    out, while the failure message can still name which file differs.
    """
    lines = sorted(f"{name}\0{digest(payload)}\n" for name, payload in files.items())
    return hashlib.sha256("".join(lines).encode()).hexdigest()


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
    for tree in TREES:
        yield from _tree_problems(root, tree)


def _tree_problems(root: Path, tree: VendoredTree) -> Iterator[str]:
    base = tree.location(root)
    present = {
        path.relative_to(base).as_posix(): path.read_bytes()
        for path in base.rglob("*")
        if path.is_file()
    }
    kept = [local_name(member) for member in tree.members]
    missing = [name for name in kept if name not in present]
    for name in missing:
        yield f"{tree.path}/{name} is missing; run tools/vendor_assets.py"
    # A stray file is a problem too: the half a per-file list cannot see.
    for name in sorted(set(present) - set(kept)):
        yield f"{tree.path}/{name} is not in the manifest; delete it or pin it"
    if missing:
        return
    found = tree_digest(present)
    if found != tree.sha256:
        yield (
            f"{tree.path} hashes to {found}, not the pinned "
            f"{tree.sha256 or '<nothing>'}"
        )
