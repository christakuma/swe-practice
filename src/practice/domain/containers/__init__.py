"""The container check engine: eight pure assertions over a `BuildQuery`.

The fourth exercise kind's grading vocabulary (Phase 22, ADR 0030), and a
sibling of `domain/checks/` and `domain/drills/` rather than an extension of
either. What each package grades, which is the thing to understand first:

* `domain/checks/`: a **repository**, through `RepoQuery`.
* `domain/drills/`: a **database and a result set**, through `DrillQuery`.
* `domain/containers/`: a **container definition**, through `BuildQuery`,
  meaning the Dockerfile and compose file as Docker would read them, not the
  text a solver typed and not an image a daemon built.

Two families, by what each reads:

* `image.py`: the build and the process it ends in. Seven assertions.
* `compose.py`: one service in compose's long form. One assertion.
"""

from practice.domain.containers.evaluation import ContainerContext, ContainerFunction
from practice.domain.containers.registry import (
    CONTAINER_ASSERTIONS,
    CONTAINER_CHECKS,
    evaluate,
    family_of,
    is_registered,
    suggest,
)

__all__ = [
    "CONTAINER_ASSERTIONS",
    "CONTAINER_CHECKS",
    "ContainerContext",
    "ContainerFunction",
    "evaluate",
    "family_of",
    "is_registered",
    "suggest",
]
