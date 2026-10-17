"""The container adapter: parse a Dockerfile and compose file, and grade them.

Phase 22's engine (ADR 0030), and the one adapter in the project that grades
without executing anything. A git scenario runs `git`, a kata runs `pytest`
and a drill runs SQLite in memory. This one reads files, because the thing
it would otherwise run is a Docker daemon, and that cannot be relied on
offline on both CI platforms. The whole package is pure parsing over text
handed in, so it needs no entry in `test_architecture.py`'s lists.

* `dockerfile.py`: the parser, and process composition.
* `dockerignore.py`: which context files the build can see.
* `compose.py`: compose's long form, whichever spelling the file used.
* `build_query.py`: `ParsedBuildQuery`, the real `BuildQuery`.
* `grader.py`: `ContainerGrader`.
"""

from practice.adapters.container.build_query import ParsedBuildQuery, context_files
from practice.adapters.container.compose import ComposeError, parse_compose
from practice.adapters.container.dockerfile import DockerfileError, parse
from practice.adapters.container.dockerignore import IgnoreRules
from practice.adapters.container.grader import (
    DEFINITION_CHECK_ID,
    ContainerGrader,
    ContainerGraderError,
    definition_report,
    grade_query,
)

__all__ = [
    "DEFINITION_CHECK_ID",
    "ComposeError",
    "ContainerGrader",
    "ContainerGraderError",
    "DockerfileError",
    "IgnoreRules",
    "ParsedBuildQuery",
    "context_files",
    "definition_report",
    "grade_query",
    "parse",
    "parse_compose",
]
