"""Say which open attempt the solver has in front of them.

The write half of ADR 0026, and the only thing in the application that writes
the mark `FindCurrentAttempt` reads. Three callers, one for each way an attempt
gets in front of somebody: `practice start`, `practice resume`, and a workbench
page whose tab has come to the front.

**Its own use case, called by those three, rather than a line inside
`StartAttempt` and `ResumeAttempt`** -- which is where it was first, on the
argument that a rule each surface restates is a rule one of them forgets. A
review found what that cost. Those two are *loaders* as well as acts:
`practice solve` starts an attempt and finishes it in the same breath, and
`practice submit` resumes one in order to grade it, so both took the mark from
the attempt actually being worked on, for an attempt about to be closed. And an
advisory write inside them could fail a start whose attempt was already saved.
Starting and resuming go back to writing nothing; a surface that puts an
attempt in front of a person says so here.

**And not `OpenWorkbench`'s job either**, which was tried before that. A page
loaded is not a page looked at: a link opened in a background tab would take
the mark from the attempt on screen, and with two attempts in two tabs the mark
would sit with whichever was *loaded* last however long ago the solver went
back to the other. It also made a GET write, which
`interface/web/security.py` rules out in a sentence -- a safe method is one
that "cannot change anything" -- and for a reason: the cross-origin guard does
not look at them.

**Only an attempt that is still open can be marked.** The caller that makes
this matter is a tab left open across a submission, reporting that it came to
the front about an attempt that is finished. An attempt finished *while* it
holds the mark keeps it, which is `FindCurrentAttempt`'s business; what this
refuses is a finished one taking the mark from the attempt being worked on.

**No content repository and no provisioner**, unlike its neighbours. Whether
the exercise is still in the library or the workspace still on disk is a
question about whether the attempt can be *worked on*, which the caller has
already answered: the page was drawn from it, and the two commands have just
loaded it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.errors import AttemptNotFoundError
from practice.domain.errors import AttemptStateError

if TYPE_CHECKING:
    from practice.domain.ids import AttemptId
    from practice.domain.ports import AttemptRepository

__all__ = ["MarkCurrentAttempt"]


@dataclass(frozen=True, slots=True)
class MarkCurrentAttempt:
    """Make one open attempt the current one. Changes nothing about it."""

    attempts: AttemptRepository

    def __call__(self, attempt_id: AttemptId) -> None:
        attempt = self.attempts.get(attempt_id)
        if attempt is None:
            raise AttemptNotFoundError(f"no attempt with id {attempt_id}")
        if not attempt.is_active:
            raise AttemptStateError(
                f"cannot make attempt {attempt.id.short} the current one: it is "
                f"{attempt.status.value}"
            )
        self.attempts.mark_current(attempt_id)
