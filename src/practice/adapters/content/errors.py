"""The one error a content problem is reported as.

**Why it is not a `DomainError`.** A malformed `exercise.yaml` is not an invalid
domain value — it never got as far as being one. It is a file on disk that a
human has to go and edit, so the thing the error must carry is a path and,
wherever possible, a line: a `ValidationError` traceback printed raw is
technically complete and practically useless, which is the failure the Phase 2
exit criterion is written against.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

__all__ = ["ContentError"]


class ContentError(Exception):
    """One content file could not be turned into an `Exercise`.

    `problems` is a list rather than a single message because a Pydantic
    `ValidationError` reports every field it rejected, and making an author fix
    one typo per run to discover the next is a bad way to spend an afternoon.

    **`path` is `Path | str` as of Phase 16, and the `str` is not a convenience.**
    A content pack is a single archive, so the thing an author has to be told
    about is `library.practicepack!git/amend-the-last-commit/exercise.yaml` — a
    location that is worth printing precisely and is not a path on this machine.
    Spelling it as a `Path` would render it with this platform's separators and
    imply a file somebody could open.
    """

    def __init__(self, path: Path | str, problems: Sequence[str]) -> None:
        self.path = path
        self.problems = tuple(problems)
        super().__init__(str(self))

    def __str__(self) -> str:
        body = "\n".join(f"  {problem}" for problem in self.problems)
        return f"{self.path}\n{body}" if body else str(self.path)
