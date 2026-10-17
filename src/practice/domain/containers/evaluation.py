"""What a container assertion reads, and the helpers more than one of them needs.

The `DrillContext` shape again, over a `BuildQuery`: the definition and the
author's `with:` mapping, and no `Attempt`. A container exercise has no console
for the same reason a drill has none, since the whole of what the solver did is one
file, so an assertion that took the attempt would be reaching for a command
history that does not exist.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from practice.domain.checks.evaluation import CheckResult, Params
    from practice.domain.ports import BuildQuery, Stage

__all__ = [
    "NO_DEFINITION",
    "ContainerContext",
    "ContainerFunction",
    "quote",
    "stage_of",
]

#: What a report says when there is nothing to read. The grader's synthesised
#: `definition-parsed` check carries the reason; this only has to be honest.
NO_DEFINITION: Final = "<no definition could be read>"

#: How much of an instruction a verdict quotes before it trails off.
_QUOTE_LIMIT: Final = 90


@dataclass(frozen=True, slots=True)
class ContainerContext:
    """Everything a container assertion may read: the definition and the `with:`."""

    query: BuildQuery
    params: Params


#: Every container assertion has this shape, which is what lets the registry be
#: a table: the contract `DrillFunction` states, over a different context.
type ContainerFunction = Callable[[ContainerContext], CheckResult]


def stage_of(context: ContainerContext) -> tuple[Stage | None, str]:
    """The stage a check names with `stage:`, or the final one, and how to say so.

    **The final stage by default, because it is the image that ships.** A
    builder stage running as root with a compiler in it is the point of a
    multi-stage build rather than a defect, so an assertion that looked at every
    stage would fail the answer the lesson is teaching.
    """
    stages = context.query.stages()
    wanted = context.params.optional_text("stage")
    if wanted is None:
        return (stages[-1] if stages else None), "the final stage"
    for stage in stages:
        if stage.name == wanted:
            return stage, f"stage {wanted!r}"
    return None, f"stage {wanted!r}"


def quote(text: str) -> str:
    """One line of a definition, short enough to sit in a verdict's `actual`."""
    flat = " ".join(text.split())
    if len(flat) <= _QUOTE_LIMIT:
        return flat
    return flat[: _QUOTE_LIMIT - 3] + "..."
