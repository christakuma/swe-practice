"""Which build-context files `.dockerignore` keeps out, by Docker's rules.

Three rules from the builder's own matcher, each one a way a hand-rolled
`fnmatch` gets the secrets exercise wrong:

* **A pattern excludes a directory's contents by matching the directory.**
  `node_modules` keeps out `node_modules/a/b.js`, so a match is tried against
  the path *and every parent of it*.
* **`*` stops at a slash and `**` does not.** `*.env` matches `.env` at the
  root and not `config/.env`; `**/*.env` matches both.
* **The last matching line wins**, so `!` re-includes: `*.md` then
  `!README.md` keeps the README.

Leading `/` and `./` are stripped, because the context root is the only root
there is and Docker normalises them away too.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = ["IgnoreRules", "glob_matcher", "normalise_path"]


class IgnoreRules:
    """The parsed `.dockerignore`, as an ordered list of `(pattern, excludes)`."""

    __slots__ = ("_rules",)

    def __init__(self, text: str = "") -> None:
        rules: list[tuple[re.Pattern[str], bool]] = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            excludes = not line.startswith("!")
            pattern = line if excludes else line[1:].strip()
            pattern = normalise_path(pattern)
            if pattern:
                rules.append((glob_matcher(pattern), excludes))
        self._rules = tuple(rules)

    def excludes(self, path: str) -> bool:
        """Whether the context file at `path` (slash-separated) is left out."""
        candidates = _self_and_parents(normalise_path(path))
        verdict = False
        for pattern, excludes in self._rules:
            if any(pattern.fullmatch(candidate) for candidate in candidates):
                verdict = excludes
        return verdict

    def kept(self, paths: Iterable[str]) -> tuple[str, ...]:
        """The paths the build context actually holds, in the order given."""
        return tuple(path for path in paths if not self.excludes(path))


def normalise_path(path: str) -> str:
    """A context path as Docker compares it: slashes, no leading `./` or `/`."""
    path = path.replace("\\", "/")
    while path.startswith(("./", "/")):
        path = path[2:] if path.startswith("./") else path[1:]
    return path.rstrip("/")


def _self_and_parents(path: str) -> tuple[str, ...]:
    parts = path.split("/")
    return tuple("/".join(parts[: end + 1]) for end in range(len(parts)))


def glob_matcher(pattern: str) -> re.Pattern[str]:
    """A context-path pattern as Docker reads it, for `.dockerignore` and `COPY`."""
    out: list[str] = []
    index = 0
    while index < len(pattern):
        character = pattern[index]
        if pattern.startswith("**/", index):
            out.append("(?:.*/)?")
            index += 3
            continue
        if pattern.startswith("**", index):
            out.append(".*")
            index += 2
            continue
        if character == "*":
            out.append("[^/]*")
        elif character == "?":
            out.append("[^/]")
        elif character == "[":
            close = pattern.find("]", index + 1)
            if close == -1:
                out.append(re.escape(character))
            else:
                # Go's matcher negates a class with `^` only, as `re` does.
                out.append(pattern[index : close + 1])
                index = close
        else:
            out.append(re.escape(character))
        index += 1
    return re.compile("".join(out))
