"""Download the pinned third-party assets and verify them against the manifest.

Run once per version bump; its output is committed:

    uv run python tools/vendor_assets.py

The manifest — which files, from where, hashing to what — is
`practice.interface.web.vendor`, not this script. The reasoning is in that
module's docstring; the short version is that the test suite verifies the same
list and should not have to import a tool that is not shipped.

**This is the only module in the project that fetches anything over the network,
and it is deliberately not part of the package.** `pyproject.toml` builds a wheel
from `src/practice` alone, so nothing a user installs can reach the internet even
by accident — which is the offline claim of PLAN.md §2 expressed in the build
rather than in prose.

**On a first run, or after a version bump, this exits non-zero on purpose.** The
hash is pinned by a human who looked at what arrived; a script that wrote the
hash of whatever it had just downloaded would be verifying a download against
itself. So it fetches, writes, computes, and prints the lines to paste.
"""

from __future__ import annotations

import sys
import urllib.error
import urllib.request
from typing import TYPE_CHECKING, Final

from practice.interface.web.vendor import ASSETS, digest, static_root, verify

if TYPE_CHECKING:
    from pathlib import Path

#: Long enough for a slow mirror, short enough that a hung CDN is not a hung
#: terminal. Nothing here retries: a failed fetch is a thing to look at.
_TIMEOUT: Final = 30.0


def fetch(url: str) -> bytes:
    """The bytes at `url`, or a readable failure.

    `urlopen` rather than a dependency, because adding `httpx` to the *runtime*
    set for a script that runs twice a year is the wrong trade — and this file is
    outside the package, so it cannot use the test suite's copy.
    """
    request = urllib.request.Request(  # noqa: S310  (https, pinned in the manifest)
        url, headers={"User-Agent": "swe-practice-vendor"}
    )
    with urllib.request.urlopen(request, timeout=_TIMEOUT) as response:  # noqa: S310
        payload: bytes = response.read()
    return payload


def download(static: Path) -> list[str]:
    """Fetch every asset into `static/`, returning what each one hashed to.

    Written in binary mode with no newline translation, which matters on Windows:
    text mode would turn every LF into CRLF and change every hash. The same rule
    `.gitattributes` applies to these files with `-text`.
    """
    lines: list[str] = []
    for asset in ASSETS:
        location = asset.location(static)
        location.parent.mkdir(parents=True, exist_ok=True)
        try:
            payload = fetch(asset.url)
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"  FAIL {asset.path}: {exc}")
            lines.append(f'{asset.path}: sha256=""  # download failed')
            continue
        location.write_bytes(payload)
        found = digest(payload)
        print(f"  ok   {asset.path}  {len(payload):>7} bytes  {found}")
        lines.append(f'{asset.path}: sha256="{found}"')
    return lines


def main() -> int:
    static = static_root()
    print(static)
    computed = download(static)

    problems = verify(static)
    if not problems:
        print(f"\n{len(ASSETS)} assets match the pinned hashes.")
        return 0

    print("")
    for problem in problems:
        print(f"  FAIL {problem}")
    print("\nPin these in src/practice/interface/web/vendor.py:")
    for line in computed:
        print(f"  {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
