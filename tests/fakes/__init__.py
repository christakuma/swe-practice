"""Test doubles for the ports in `practice.domain.ports`.

These are the second implementation each ambient port needs to justify existing
(PLAN.md §13). `FakeRepoQuery` is the one that pays for the whole `RepoQuery`
abstraction: it computes ancestry, revision resolution and reachability from an
in-memory DAG rather than storing the answers, so it can be *wrong* — which is
what makes both the 22 assertion tests and the conformance suite in
`tests/integration/git/` evidence rather than ceremony.

`content`, `sandbox`, `kata` and `editor` are what make the application tests
cheap: between them they stand in for an exercise library, a provisioned
directory, a git environment, a pytest subprocess and the solver's own editor,
so a test about the *ordering* of a use case costs a millisecond rather than ten
seconds. They are held to the real
adapters' behaviour wherever it is observable — `attach` returning `None`,
`read_file` raising `OSError` — on the principle that a fake allowed to differ
makes its tests prove nothing.
"""

from tests.fakes.clock import FakeClock
from tests.fakes.content import FakeContentRepository, a_kata, a_scenario
from tests.fakes.editor import FakeEditorLauncher
from tests.fakes.ids import SequentialIdGenerator
from tests.fakes.kata import StubKataRunner, a_record, a_run, a_timeout
from tests.fakes.repo import (
    BuilderRepoQueryFactory,
    Commit,
    FakeRepoQuery,
    RepoBuilder,
    RepoState,
    a_repo,
)
from tests.fakes.sandbox import FakeProvisioner, FakeWorkspace
from tests.fakes.scheduling import FixedScheduler, Scheduled

__all__ = [
    "BuilderRepoQueryFactory",
    "Commit",
    "FakeClock",
    "FakeContentRepository",
    "FakeEditorLauncher",
    "FakeProvisioner",
    "FakeRepoQuery",
    "FakeWorkspace",
    "FixedScheduler",
    "RepoBuilder",
    "RepoState",
    "Scheduled",
    "SequentialIdGenerator",
    "StubKataRunner",
    "a_kata",
    "a_record",
    "a_repo",
    "a_run",
    "a_scenario",
    "a_timeout",
]
