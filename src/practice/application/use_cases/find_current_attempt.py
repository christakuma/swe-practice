"""Which attempt somebody means by "this", when they do not say.

The read half of ADR 0026, and the whole rule in one place. An MCP client asks
about "my attempt" with no id; this answers with one, or says honestly that
there is no answer.

**The marked attempt, whether or not it has been finished since.** The first
version of the rule lived in the MCP adapter and looked only at what was open,
and a review found the hole on the path everybody walks: leave one attempt
unfinished, work a second, submit it, ask what went wrong -- and the only open
attempt is the stale one, so the tutor described *that*, with the verdict for
the other on screen. The mark knew better and was not asked. A solver who
submits an attempt is still looking at it; what moves the mark off it is
getting in front of another one, which `MarkCurrentAttempt` records.

**Except an abandoned one.** Abandoning is the solver saying they are done
with an attempt without wanting it graded, so there is no verdict to go over
and nothing they would mean by "this". The rule falls through as though
nothing were marked.

**With no usable mark, the only open attempt, and otherwise nothing.** One
open attempt needs no choosing, which is also every database written before
the mark existed. Several is where ADR 0024's refusal survives: the next most
recent would be a guess, and a tutor confidently describing the wrong
repository is the failure the refusal exists to prevent. `None` covers both
"nothing is open" and "several are", because what to *say* about each is the
caller's business and it already has `ListOpenAttempts` to say it with.

**Not on `ListOpenAttempts`, where it started.** A flag on every open attempt
cost every page that lists them a second read for a fact only two listings
show, and could not express the case above at all: the attempt that is
current may not be in the list.

**It is handed the open attempts rather than loading them**, which is the
other half of the same economy. All three callers -- the MCP server's resolver
and its listing, and `practice attempts` -- hold that list already, to print or
to refuse with, and the version that fetched its own read the table twice for
each of them. So this reads one id, and one attempt only when the mark names
something that is no longer open.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.domain.attempt import AttemptStatus

if TYPE_CHECKING:
    from collections.abc import Sequence

    from practice.application.dto import OpenAttempt
    from practice.domain.ids import AttemptId
    from practice.domain.ports import AttemptRepository

__all__ = ["FindCurrentAttempt"]


@dataclass(frozen=True, slots=True)
class FindCurrentAttempt:
    """The attempt in front of the solver, or `None` when nothing says. Reads."""

    attempts: AttemptRepository

    def __call__(self, still_open: Sequence[OpenAttempt]) -> AttemptId | None:
        """`still_open` is what `ListOpenAttempts` returned, a moment ago."""
        marked = self.attempts.current()
        if marked is not None:
            if any(found.attempt.id == marked for found in still_open):
                return marked
            attempt = self.attempts.get(marked)
            # A mark can outlive its row only if somebody deleted the row by
            # hand, and the honest reading of that is the same as no mark.
            if attempt is not None and attempt.status is not AttemptStatus.ABANDONED:
                return marked

        if len(still_open) == 1:
            return still_open[0].attempt.id
        return None
