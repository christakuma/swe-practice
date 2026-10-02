"""What an assertion is, what it is given, and what it hands back.

The three types every check function in this package shares, and the two
decisions that shape all 22 of them.

**An assertion returns a `CheckResult`, not a `CheckReport`.** It says what it
expected, what it found, and whether those agree — and nothing about the
exercise. One dispatcher (`registry.evaluate`) then applies `not:` and carries the
author's label, severity and explanation across through `CheckReport.from_spec`.

That split is what keeps negation a single mechanism rather than 22 copies of one.
PLAN.md §6.3 made `not:` a uniform modifier instead of a set of paired opposites,
and a function that built its own report would have to invert its own `passed`
*and* rewrite its own `expected` string — twenty-two chances to get it wrong, and
the one that got it wrong would report a failure as a pass.

The cost is a convention: **`expected` is a noun phrase**, so that negating it
reads as `not <phrase>`. "a detached HEAD", not "HEAD is detached".

**A broken `with:` mapping fails cleanly, like a missing ref.** `Params` raises
`CheckSpecError` for a parameter that is absent or the wrong type, and the
dispatcher turns that into a failing report naming the exercise's own bug. PLAN.md
§6.5 requires this of a missing ref — a traceback in the verdict panel teaches
nothing — and an authoring mistake deserves the same treatment for the same
reason: the person reading the verdict is a solver who cannot act on it. What
*can* act on it is CI, where the graded replay of every reference solution turns
it into a build failure before anyone sees it (§9).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from practice.domain.errors import DomainError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

    from practice.domain.attempt import Attempt
    from practice.domain.exercise import ParamValue
    from practice.domain.ids import Sha
    from practice.domain.ports import RepoQuery

__all__ = [
    "MISSING",
    "CheckContext",
    "CheckFunction",
    "CheckResult",
    "CheckSpecError",
    "Params",
    "compare",
    "describe",
    "matcher",
    "resolve",
]

#: A fixture alias, exactly as PLAN.md §6.5 specifies it. Aliases are resolved
#: from the alias map **before git ever sees the string**, so they can never be
#: confused with git's own `@` syntax — `HEAD@{1}` is git's, `@c2` is ours.
_ALIAS: Final = re.compile(r"^@([A-Za-z][A-Za-z0-9_-]*)$")

#: What a report says about a revision that does not resolve. One string, used
#: everywhere, so a verdict never has two spellings of the same situation.
MISSING: Final = "<does not exist>"

#: The comparison keys `commit_count` and `stash_count` accept. Exactly one of
#: them must be present: a check that silently defaulted to `at_least: 0` would
#: pass unconditionally, which is the vacuous-check failure §5.4 is about.
_COMPARISONS: Final = ("equals", "at_least", "at_most")


class CheckSpecError(DomainError):
    """An exercise's `with:` mapping cannot be evaluated as written.

    An authoring bug, not a solver mistake — which is why it never reaches the
    solver as a traceback. `registry.evaluate` catches it and reports a failing
    check whose `actual` names the problem, and CI's graded replay turns the same
    condition into a build failure (§9).
    """


@dataclass(frozen=True, slots=True)
class CheckResult:
    """What one assertion found, before the exercise's words are attached.

    `expected` is a **noun phrase**, so `negate` can prefix it — see the module
    docstring. `actual` is free-form, because the interesting cases are the ones
    no type could hold: `<does not exist>`, `3 commits`, `refs/heads/main`.
    """

    passed: bool
    expected: str
    actual: str

    def negate(self) -> CheckResult:
        """Flip the verdict and say so, for a check carrying `not: true`.

        The one place negation happens. `actual` is untouched: what was found is
        what was found, and only the judgement about it inverts.
        """
        return CheckResult(
            passed=not self.passed,
            expected=f"not {self.expected}",
            actual=self.actual,
        )


@dataclass(frozen=True, slots=True)
class CheckContext:
    """Everything an assertion may read.

    `query` for the repository, `attempt` for the command log, `params` for the
    author's `with:` mapping. Three things and no more: an assertion that needed
    the `Exercise` would be reaching for the label it has deliberately not been
    given, and one that needed a filesystem path would not be a pure function.
    """

    query: RepoQuery
    attempt: Attempt
    params: Params


#: Every assertion has this shape, which is what lets the registry be a table.
type CheckFunction = Callable[[CheckContext], CheckResult]


@dataclass(frozen=True, slots=True)
class Params:
    """Typed access to an author's `with:` mapping.

    Every accessor raises `CheckSpecError` rather than returning a default for a
    parameter it needs. A default would be the friendlier choice and the wrong
    one: `is_ancestor` with no `ancestor:` has nothing to compare, and the only
    honest answers are "refuse" or "silently grade something else".

    Where a default genuinely is the right behaviour it is passed explicitly —
    `flag("include_untracked", default=False)` is PLAN.md §6.5's rule about
    untracked files, written down where it applies.
    """

    assertion: str
    values: Mapping[str, ParamValue]

    def text(self, name: str, *, default: str | None = None) -> str:
        """A string parameter: a revision, a ref name, a path, a pattern."""
        value = self._get(name, default)
        if not isinstance(value, str):
            raise self._wrong(name, value, "a string")
        if not value.strip():
            raise CheckSpecError(f"{self.assertion}: {name!r} is empty")
        return value

    def optional_text(self, name: str) -> str | None:
        """A string parameter that may be absent, where absence *means* something.

        Distinct from `text(name, default=...)`, which substitutes a value: here
        `None` is the answer, and the caller branches on it. `no_conflict_markers`
        is the case — no `ref:` means "read the working tree", which is a different
        question rather than a different revision, so there is no default revision
        that could stand in for it.
        """
        if name not in self.values:
            return None
        return self.text(name)

    def integer(self, name: str) -> int:
        """An integer parameter. A `bool` is refused even though Python says it is
        one: `commit_count {equals: true}` is a typo, not a count of one.
        """
        value = self._get(name, None)
        if isinstance(value, bool) or not isinstance(value, int):
            raise self._wrong(name, value, "an integer")
        return value

    def flag(self, name: str, *, default: bool) -> bool:
        """A boolean parameter, which always has a default — see the class docstring."""
        if name not in self.values:
            return default
        value = self.values[name]
        if not isinstance(value, bool):
            raise self._wrong(name, value, "true or false")
        return value

    def paths(self, name: str) -> tuple[str, ...]:
        """A list of paths. A bare string is accepted as a list of one.

        Accepting both is a kindness with a reason: YAML makes
        `with: {paths: src/a.py}` and `with: {paths: [src/a.py]}` look equally
        correct, and refusing the first would be refusing an exercise that is
        already unambiguous.
        """
        value = self._get(name, None)
        if isinstance(value, str):
            return (value,)
        if not isinstance(value, tuple) or not value:
            raise self._wrong(name, value, "a non-empty list of paths")
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise self._wrong(name, value, "a list of non-empty paths")
        return tuple(str(item) for item in value)

    def comparison(self) -> tuple[str, int]:
        """The one comparison key a counting assertion carries, and its value.

        Exactly one. Zero is a check that passes unconditionally; two is an
        author who meant one of them and will never find out which was used.
        """
        present = [name for name in _COMPARISONS if name in self.values]
        if len(present) != 1:
            raise CheckSpecError(
                f"{self.assertion}: needs exactly one of "
                f"{', '.join(_COMPARISONS)}, got "
                f"{', '.join(present) if present else 'none'}"
            )
        return present[0], self.integer(present[0])

    def _get(self, name: str, default: str | None) -> ParamValue:
        if name in self.values:
            return self.values[name]
        if default is not None:
            return default
        raise CheckSpecError(f"{self.assertion}: missing required parameter {name!r}")

    def _wrong(self, name: str, value: object, wanted: str) -> CheckSpecError:
        return CheckSpecError(
            f"{self.assertion}: {name!r} must be {wanted}, got {value!r}"
        )


def resolve(query: RepoQuery, rev: str) -> Sha | None:
    """Turn a `ref:` or `target:` into a hash, or `None` if it does not resolve.

    Aliases first, and that order is the point (PLAN.md §6.5): `@c2` is matched
    against the fixture's alias map and resolved to a hash before git is asked
    anything, so it can never collide with git's own `@` syntax. An alias the
    fixture never recorded is a miss, not an error — which is a real authoring
    mistake the content suite catches by checking every alias a check names
    against what the fixture produced.

    Worth repeating here because it bites content authors: **`@c2` is assertion
    syntax only.** It must not appear in `solution.cmds`, because a solver cannot
    type it — they only ever see real revisions.
    """
    alias = _ALIAS.match(rev)
    if alias is not None:
        return query.aliases().get(alias[1])
    return query.rev_parse(rev)


def describe(sha: Sha | None) -> str:
    """A hash for a report, or the one spelling of a revision that is not there."""
    return sha.short if sha is not None else MISSING


def compare(operator: str, actual: int, wanted: int) -> bool:
    """Apply a comparison from `Params.comparison`.

    A mapping rather than a chain of branches, so an operator added to
    `_COMPARISONS` without a rule here is a `KeyError` at the only moment it can
    be noticed — in the test that adds it — rather than a silent pass.
    """
    return {
        "equals": actual == wanted,
        "at_least": actual >= wanted,
        "at_most": actual <= wanted,
    }[operator]


def matcher(params: Params, name: str = "pattern") -> re.Pattern[str]:
    """Compile an author's regular expression, or refuse the exercise.

    Unanchored, because the patterns in `content/` rely on it:
    `push\\b.*--force` is meant to match anywhere in a command line, and an
    author who wants anchoring writes `^` as they already do.

    A pattern that will not compile is a `CheckSpecError` rather than an escaped
    `re.error`, for the reason the whole module exists: the person reading the
    verdict cannot fix the exercise, and CI can.
    """
    pattern = params.text(name)
    try:
        return re.compile(pattern)
    except re.error as exc:
        raise CheckSpecError(
            f"{params.assertion}: {name!r} is not a valid regular expression: {exc}"
        ) from exc
