"""Test doubles for the ports in `practice.domain.ports`.

These are the second implementation each ambient port needs to justify existing
(PLAN.md §13). `FakeRepoQuery` — the one that pays for the whole `RepoQuery`
abstraction — arrives with the check engine in Phase 5, where there are
assertions to point at it.

`content`, `sandbox` and `kata` are what make the application tests cheap:
between them they stand in for an exercise library, a provisioned directory, a
git environment and a pytest subprocess, so a test about the *ordering* of a use
case costs a millisecond rather than ten seconds. They are held to the real
adapters' behaviour wherever it is observable — `attach` returning `None`,
`read_file` raising `OSError` — on the principle that a fake allowed to differ
makes its tests prove nothing.
"""

from tests.fakes.clock import FakeClock
from tests.fakes.content import FakeContentRepository, a_kata, a_scenario
from tests.fakes.ids import SequentialIdGenerator
from tests.fakes.kata import StubKataRunner, a_record, a_run, a_timeout
from tests.fakes.sandbox import FakeProvisioner, FakeWorkspace

__all__ = [
    "FakeClock",
    "FakeContentRepository",
    "FakeProvisioner",
    "FakeWorkspace",
    "SequentialIdGenerator",
    "StubKataRunner",
    "a_kata",
    "a_record",
    "a_run",
    "a_scenario",
    "a_timeout",
]
