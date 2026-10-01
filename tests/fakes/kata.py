"""A kata runner that returns whatever a test tells it to.

The second implementation of `adapters.kata.grader.KataRunner`, and the reason
that protocol exists: every branch in the grader — a clean pass, a mixed run, a
timeout, a collection error, a report that could not be read — becomes a
millisecond-long unit test instead of a subprocess. The timeout case is the one
that pays for it outright: proving the grader handles a killed suite otherwise
means waiting out a real time limit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from practice.adapters.kata.pytest_runner import KataRun, TestOutcome, TestRecord
from practice.adapters.sandbox.execution import TIMEOUT_EXIT_CODE

if TYPE_CHECKING:
    from collections.abc import Sequence

    from practice.domain.exercise import KataSpec
    from practice.domain.ports import Workspace

__all__ = ["StubKataRunner", "a_record", "a_run", "a_timeout"]


def a_record(
    name: str,
    *,
    outcome: TestOutcome = TestOutcome.PASSED,
    doc: str | None = None,
    message: str | None = None,
    location: str | None = None,
) -> TestRecord:
    """One record, with the nodeid spelled the way pytest spells it."""
    return TestRecord(
        nodeid=f"tests.py::{name}",
        outcome=outcome,
        doc=doc,
        message=message,
        location=location,
        duration_ms=1,
    )


def a_run(*records: TestRecord, exit_code: int | None = None) -> KataRun:
    """A finished run. The exit code defaults to agreeing with the records."""
    failed = any(not record.passed for record in records)
    return KataRun(
        tests=records,
        exit_code=exit_code if exit_code is not None else int(failed),
        exit_status=int(failed),
        duration_ms=len(records),
    )


def a_timeout(output: str = "") -> KataRun:
    """A run killed by the time limit: no records, exit code 124."""
    return KataRun(tests=(), exit_code=TIMEOUT_EXIT_CODE, output=output)


class StubKataRunner:
    """Satisfies `KataRunner` by handing back a canned run."""

    def __init__(self, run: KataRun) -> None:
        self._run = run
        self.calls: list[tuple[str, str]] = []

    def run(self, workspace: Workspace, spec: KataSpec, source: str) -> KataRun:
        """Records what it was asked, so a test can assert the source reached it."""
        del workspace
        self.calls.append((spec.tests, source))
        return self._run

    @property
    def sources(self) -> Sequence[str]:
        return [source for _, source in self.calls]
