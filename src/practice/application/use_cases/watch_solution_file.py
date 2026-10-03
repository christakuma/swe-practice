"""Grade the solver's file every time they save it, and persist nothing.

The second half of own-editor mode, and the decision in it is the whole of
ADR 0013: **grade-on-save is a preview, not a submission.**

The obvious implementation is to call `SubmitSolution` on every save. It cannot
work, and the reason is a rule rather than a bug: submission *completes* the
attempt, and `Attempt` refuses to complete twice (§4.3) — so the first Ctrl+S
would end the exercise and the second would be told the attempt is finished. The
next idea is to append a `SolutionSaved` event per save and grade from the log,
which works and is worse: Phase 8 settled that an editor save is a keystroke
rather than something the solver *did in the exercise* (PLAN.md §16), and a log
with forty of them in it would make every §6.3 process assertion learn to ignore
a kind of entry, and would turn `latest_source` into a record of whichever save
happened to be last rather than of what was submitted.

So nothing is written. On each save this loads the attempt, hands it the source
**in memory**, grades it, and throws the aggregate away:

    attempt = self.attempts.get(attempt_id)   # a fresh aggregate
    attempt.save_solution(source, at=now)     # in memory only
    verdict = grader.grade(exercise, workspace, attempt)
    # and it is never saved

That keeps the property the `Grader` port is shaped around — *a verdict is
derived from a source the attempt remembers*, which is why `grade` takes an
`Attempt` and not a string — while leaving the stored log untouched. The event
exists for the length of one grading pass, which is exactly how long the claim
needs to hold. Submitting is still a thing the solver does on purpose, with a
button.

**The refusals are raised eagerly, before any streaming starts.** `__call__` is
an ordinary method that resolves the file and then returns the generator, rather
than being an `async def` generator itself: an async generator's body does not
run until the first `__anext__`, so an attempt that does not exist would have
raised *inside* a response that had already begun. The web layer needs to know
before it commits to a stream.

**A save that cannot be read is skipped rather than reported.** Editors save by
writing a temporary file and renaming it over the target, so there is a window
in which the path exists and is not readable — and the rename itself produces
another event a few milliseconds later. Reporting the first as an error would
put a transient `FileNotFoundError` in front of a solver who did nothing wrong.

**An attempt that is no longer active ends the stream**, and it does so through
`Attempt.save_solution` refusing rather than through a check here: submitting
from the browser tab closes the attempt, and the sentence the aggregate raises —
*cannot save a solution: attempt 18ec95b0 is completed* — is already the right
one. The attempt is re-read on every save for exactly this reason; a stream
holding the aggregate it started with would go on grading an exercise that had
finished.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import Draft
from practice.application.errors import AttemptNotFoundError
from practice.application.use_cases.reveal_solution_file import load_solution_file

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from practice.application.registry import GraderRegistry
    from practice.application.use_cases.reveal_solution_file import SolutionFile
    from practice.domain.ids import AttemptId
    from practice.domain.ports import (
        AttemptRepository,
        Clock,
        ContentRepository,
        FileWatcher,
        Grader,
        SandboxProvisioner,
    )

__all__ = ["WatchSolutionFile"]


@dataclass(frozen=True, slots=True)
class WatchSolutionFile:
    """A verdict per save, for as long as somebody is listening."""

    content: ContentRepository
    attempts: AttemptRepository
    provisioner: SandboxProvisioner
    graders: GraderRegistry
    clock: Clock
    watcher: FileWatcher

    def __call__(self, attempt_id: AttemptId) -> AsyncGenerator[Draft | None]:
        """Resolve the file now; yield a draft per save after that.

        `None` is yielded for the watcher's periodic tick -- nothing has
        happened, and the caller holding a connection gets its chance to notice
        that nobody is on the other end of it (`FileWatcher` in
        `domain/ports.py` has the argument).

        Typed as the generator it is rather than as an `AsyncIterator`, so a
        caller that stops early can `aclose()` it. That is not a nicety: the
        generator holds a live file watch, and leaving it to be collected leaves
        the watch running for as long as that takes -- which would undo the
        reason the tick exists.
        """
        found = load_solution_file(
            attempt_id,
            content=self.content,
            attempts=self.attempts,
            provisioner=self.provisioner,
        )
        grader = self.graders.for_exercise(found.exercise)
        return self._drafts(attempt_id, found, grader)

    async def _drafts(
        self, attempt_id: AttemptId, found: SolutionFile, grader: Grader
    ) -> AsyncGenerator[Draft | None]:
        async for changed in self.watcher.changes(found.path):
            if not changed:
                yield None
                continue
            # Off the event loop, all of it. Grading a kata starts a pytest
            # subprocess and waits up to the exercise's time limit for it, and
            # reading the attempt back is a SQLite query -- so a stream that did
            # either inline would stall every other request in the server for as
            # long as it took. `asyncio.to_thread` rather than Starlette's
            # `run_in_threadpool` because this layer may not import a web
            # framework; it is the same mechanism underneath.
            draft = await asyncio.to_thread(self._draft, attempt_id, found, grader)
            if draft is not None:
                yield draft

    def _draft(
        self, attempt_id: AttemptId, found: SolutionFile, grader: Grader
    ) -> Draft | None:
        """One grading pass over what is in the file. `None` if it was mid-save.

        Blocking, and called in a thread. Nothing it touches is saved -- see the
        module docstring.
        """
        attempt = self.attempts.get(attempt_id)
        if attempt is None:
            # The row went away under a live stream: `practice gc` cannot do
            # this, but a developer with a sqlite shell can, and the honest
            # answer is the same one every other use case gives.
            raise AttemptNotFoundError(f"no attempt with id {attempt_id}")

        try:
            source = found.workspace.read_file(found.relative)
        except OSError:
            return None

        attempt.save_solution(source, at=self.clock.now())
        verdict = grader.grade(found.exercise, found.workspace, attempt)
        return Draft(source=source, verdict=verdict)
