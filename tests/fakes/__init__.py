"""Test doubles for the ports in `practice.domain.ports`.

These are the second implementation each ambient port needs to justify existing
(PLAN.md §13). `FakeRepoQuery` — the one that pays for the whole `RepoQuery`
abstraction — arrives with the check engine in Phase 5, where there are
assertions to point at it.

`sandbox` and `kata` are what make the grading tests cheap: between them they
stand in for a provisioned directory, a git environment and a pytest
subprocess, so a test about how a run maps to a verdict costs a millisecond
rather than ten seconds. They are held to the real adapters' behaviour where it
is observable — `attach` returning `None`, `read_file` raising `OSError` — on
the principle that a fake allowed to differ makes its tests prove nothing.
"""

from tests.fakes.clock import FakeClock
from tests.fakes.ids import SequentialIdGenerator
from tests.fakes.kata import StubKataRunner, a_record, a_run, a_timeout
from tests.fakes.sandbox import FakeProvisioner, FakeWorkspace

__all__ = [
    "FakeClock",
    "FakeProvisioner",
    "FakeWorkspace",
    "SequentialIdGenerator",
    "StubKataRunner",
    "a_record",
    "a_run",
    "a_timeout",
]
