"""Identifiers and the small scalar value objects shared across the domain.

Every one of these validates on construction, so an invalid identifier cannot
exist anywhere downstream. That is the whole reason they are types rather than
bare `str`: the alternative is a `str` that is checked at the edges and trusted
everywhere else, which holds until the first code path that forgot.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, NewType
from uuid import UUID

from practice.domain.errors import InvalidValueError

__all__ = ["AttemptId", "ExerciseId", "Sha", "Tag", "tag"]

# Lowercase, hyphen-separated, no leading or trailing hyphen. The same shape is
# used for exercise id segments, tags, and check ids, because all three end up
# in URLs, directory names, and YAML keys.
_SLUG: Final = r"[a-z0-9]+(?:-[a-z0-9]+)*"

_EXERCISE_ID: Final = re.compile(rf"^(?P<track>{_SLUG})/(?P<slug>{_SLUG})$")
_TAG: Final = re.compile(rf"^{_SLUG}$")

# SHA-1 today; 64 is allowed because git's object format is a per-repository
# setting and a future SHA-256 default would otherwise invalidate this type
# rather than just the recorded hashes (PLAN.md §6.1).
_SHA: Final = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")

_SHORT_SHA_LENGTH: Final = 7
_SHORT_ATTEMPT_ID_LENGTH: Final = 8


@dataclass(frozen=True, slots=True, order=True)
class ExerciseId:
    """A content slug: exactly `<track>/<slug>`, e.g. `git/recover-a-lost-commit`.

    Exactly two segments, because the id *is* the content path — `content/git/
    recover-a-lost-commit/` — and a loader that derives ids from directories and
    a type that accepts any depth would disagree the first time someone nests a
    directory. Ordered so exercise listings sort deterministically without the
    caller inventing a key.
    """

    value: str

    def __post_init__(self) -> None:
        if not _EXERCISE_ID.match(self.value):
            raise InvalidValueError(
                f"exercise id must be '<track>/<slug>' in lowercase kebab-case, "
                f"got {self.value!r}"
            )

    @property
    def track(self) -> str:
        """The first segment — `git`, `katas`."""
        return self.value.split("/", 1)[0]

    @property
    def slug(self) -> str:
        """The second segment — the exercise's own name."""
        return self.value.split("/", 1)[1]

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class AttemptId:
    """A uuid4 in practice, though the type does not insist on version 4.

    Generated through the `IdGenerator` port rather than here: a `new()`
    classmethod would put a source of randomness inside the pure layer, and
    every test that wants a stable snapshot would have to patch it.
    """

    value: UUID

    @classmethod
    def parse(cls, text: str) -> AttemptId:
        """Build one from its string form, as persistence hands it back."""
        try:
            return cls(UUID(text))
        except ValueError as exc:
            raise InvalidValueError(f"not a valid attempt id: {text!r}") from exc

    @property
    def short(self) -> str:
        """The first 8 hex characters, used for the workspace directory name.

        Short on purpose: Windows `MAX_PATH` is 260 characters unless long paths
        are enabled, and a full 36-character uuid plus a nested fixture tree gets
        uncomfortably close (PLAN.md §8.1).
        """
        return self.value.hex[:_SHORT_ATTEMPT_ID_LENGTH]

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class Sha:
    """A git object hash.

    Normalised to lowercase on construction. Git emits lowercase, but a fixture
    alias file or a hand-written test literal may not, and two `Sha` values that
    differ only in case comparing unequal would be a genuinely nasty bug in an
    assertion engine that compares hashes for a living.
    """

    value: str

    def __post_init__(self) -> None:
        normalised = self.value.strip().lower()
        if not _SHA.match(normalised):
            raise InvalidValueError(f"not a git object hash: {self.value!r}")
        object.__setattr__(self, "value", normalised)

    @property
    def short(self) -> str:
        """The 7-character abbreviation git itself uses for display."""
        return self.value[:_SHORT_SHA_LENGTH]

    def __str__(self) -> str:
        return self.value


# A `NewType` rather than a class: tags are used in sets, sorted, and formatted
# as plain strings everywhere, and wrapping them would buy nothing but
# `.value`. mypy still refuses to mix `tuple[Tag, ...]` with `tuple[str, ...]`,
# which is the part worth having.
Tag = NewType("Tag", str)


def tag(value: str) -> Tag:
    """Validate and wrap a tag. The single place tag syntax is enforced."""
    if not _TAG.match(value):
        raise InvalidValueError(
            f"tag must be lowercase kebab-case, got {value!r}",
        )
    return Tag(value)
