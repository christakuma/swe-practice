"""The half of git that *reads* a repository.

Everything that *builds* one is `adapters/sandbox/` — the provisioner, the
fixture runner, the environment. The split is the one PLAN.md §16 settled when
`fixture_runner` could not live here without the two packages importing each
other: construction is the sandbox's job, interrogation is this package's.

Two modules:

* `repo_query` — `GitRepoQuery`, which satisfies the `RepoQuery` port by running
  `git` with machine-readable output formats through the workspace's trusted
  `run_tool` channel.
* `grader` — `ScenarioGrader`, which satisfies the `Grader` port by evaluating an
  exercise's `CheckSpec`s against one of those and assembling the reports into a
  `Verdict`.

Note what is *not* here: the 22 assertion functions. They are pure functions over
the port and live in `domain/checks/`, which is what makes "testable with no git
installed" a structural fact rather than a happy accident (§6.2). A check
function in this package would be a check function outside the coverage gate.

`RepoQueryFactory` is no longer re-exported from here. It was a protocol declared
in `grader.py` while the grader was the only thing that built a `RepoQuery`; Phase
8's repo state panel is the second, and a port two layers need belongs in
`domain/ports.py` rather than in the adapter one of them happens to live in.

PLAN.md §10 also sketched a `graph.py` for ancestry walking. It is deliberately
absent: `GitRepoQuery` asks `git merge-base --is-ancestor`, and the only code
that walks a commit graph by hand is `FakeRepoQuery` in the test suite. A module
to hold one function nothing calls is the abstraction §13 says to delete rather
than carry.
"""

from practice.adapters.git.grader import ScenarioGrader, ScenarioGraderError
from practice.adapters.git.repo_query import GIT_TIMEOUT_SECONDS, GitRepoQuery

__all__ = [
    "GIT_TIMEOUT_SECONDS",
    "GitRepoQuery",
    "ScenarioGrader",
    "ScenarioGraderError",
]
