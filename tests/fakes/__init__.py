"""Test doubles for the ports in `practice.domain.ports`.

These are the second implementation each ambient port needs to justify existing
(PLAN.md §13). `FakeRepoQuery` — the one that pays for the whole `RepoQuery`
abstraction — arrives with the check engine in Phase 5, where there are
assertions to point at it.
"""

from tests.fakes.clock import FakeClock
from tests.fakes.ids import SequentialIdGenerator

__all__ = ["FakeClock", "SequentialIdGenerator"]
