"""`name -> ContainerFunction`, and the one place `not:` is applied to one.

The third near-twin of `domain/checks/registry.py`, and it is a twin for the
reason ADR 0019 gave about the second: **a container exercise naming a git or
drill assertion has to be a build failure**, not a check that reaches a
dispatcher holding the wrong port. Three disjoint tables make that true by
construction. The shared pieces, `CheckSpec`, `Params`, `matcher`,
`suggest_from` and the dispatcher's three jobs, are imported rather than
copied.

**Eight assertions, each named by a shipped exercise**, which
`tests/content/test_containers.py` holds. The plan had ten. `stage_count` and
`service_mount` were cut because the first batch has no multi-stage or
volume exercise, and they arrive with the exercises that want them.

`family_of` knows all three vocabularies, which only this module can: it is
the newest family, so importing the other two is the dependency running the
way it already runs. The schema uses it to say *`tree_equals` is a git_scenario
assertion* in any block, rather than offering three trigram guesses.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from practice.domain.checks import registry as git_registry
from practice.domain.checks.evaluation import CheckSpecError, Params
from practice.domain.containers import compose, image
from practice.domain.containers.evaluation import ContainerContext
from practice.domain.drills import registry as drill_registry
from practice.domain.verdict import CheckReport

if TYPE_CHECKING:
    from collections.abc import Mapping

    from practice.domain.containers.evaluation import ContainerFunction
    from practice.domain.exercise import CheckSpec
    from practice.domain.ports import BuildQuery

__all__ = [
    "CONTAINER_ASSERTIONS",
    "CONTAINER_CHECKS",
    "evaluate",
    "family_of",
    "is_registered",
    "suggest",
]

#: What the image is built from, in what order, and what it runs as.
_IMAGE: Final[Mapping[str, ContainerFunction]] = {
    "base_image_matches": image.base_image_matches,
    "command_matches": image.command_matches,
    "instruction_matches": image.instruction_matches,
    "ordered_before": image.ordered_before,
    "path_in_image": image.path_in_image,
    "pid1_matches": image.pid1_matches,
    "runs_as": image.runs_as,
}

#: What a compose file declares about a service, in long form.
_COMPOSE: Final[Mapping[str, ContainerFunction]] = {
    "service_value": compose.service_value,
}

#: Name to function: the whole container vocabulary.
CONTAINER_CHECKS: Final[Mapping[str, ContainerFunction]] = MappingProxyType(
    {**_IMAGE, **_COMPOSE}
)

#: Every legal value of an `assert:` key inside a `container:` block.
CONTAINER_ASSERTIONS: Final = frozenset(CONTAINER_CHECKS)


def is_registered(name: str) -> bool:
    """Whether `name` is a legal `assert:` value inside a `container:` block."""
    return name in CONTAINER_ASSERTIONS


def evaluate(spec: CheckSpec, query: BuildQuery) -> CheckReport:
    """Run one container check and report it in the author's words.

    The three jobs every dispatcher here does: negation, the author's label,
    and a broken `with:` mapping reported as a failing check rather than a
    traceback. No `Attempt`, for the reason `ContainerContext` gives.
    """
    function = CONTAINER_CHECKS.get(spec.assertion)
    if function is None:  # pragma: no cover - the schema rejects the name first
        return CheckReport.from_spec(
            spec,
            passed=False,
            expected=f"the {spec.assertion} assertion",
            actual="<no function is registered for it>",
        )

    context = ContainerContext(
        query=query, params=Params(assertion=spec.assertion, values=spec.params)
    )
    try:
        result = function(context)
    except CheckSpecError as exc:
        return CheckReport.from_spec(
            spec,
            passed=False,
            expected=f"a usable {spec.assertion} check",
            actual=f"<this exercise is misconfigured: {exc}>",
        )

    if spec.negated:
        result = result.negate()
    return CheckReport.from_spec(
        spec, passed=result.passed, expected=result.expected, actual=result.actual
    )


def suggest(name: str, *, limit: int = 3) -> tuple[str, ...]:
    """Registered container names close enough to `name` to be worth offering."""
    return git_registry.suggest_from(name, CONTAINER_ASSERTIONS, limit=limit)


def family_of(name: str) -> str | None:
    """The exercise kind an assertion belongs to, across all three vocabularies.

    `None` for a name nobody registers, which is a typo and gets trigram
    suggestions instead. The three tables are disjoint, so at most one answers.
    """
    if name in CONTAINER_ASSERTIONS:
        return "container"
    if drill_registry.is_registered(name):
        return "sql_drill"
    if git_registry.is_registered(name):
        return "git_scenario"
    return None
