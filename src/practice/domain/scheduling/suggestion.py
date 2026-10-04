"""Reading a finished attempt as one of SM-2's four grades.

**Why the tool proposes the grade at all.** Every spaced-repetition system makes
the learner self-report, and self-reporting is where the data goes bad: the grade
is pressed in the second after an answer, by the person least able to be
objective about it. This tool has evidence nobody else's has — a verdict derived
from the end state, an event log of every hint revealed, and a wall-clock time
against the author's own estimate — so it can make the first guess and let the
solver correct it. PLAN.md §11 calls it *"an auto-suggested grade from verdict,
elapsed time and hints used"*, and those three are exactly the inputs.

**It is in `domain/` rather than behind the `Scheduler` port.** A suggestion is a
reading of an attempt, not an interval: FSRS behind the same port (§4.6) would
want this rule unchanged, and putting it inside the scheduler would make a second
algorithm re-implement it. It is also not `application/` — "how well did that go"
is a thing the product can be *right or wrong about*, which is the line §3 draws.

**The rule is three penalties against a ceiling, and the ceiling is the point.**
A pass never suggests `AGAIN`. `AGAIN` means *you did not know this*, and someone
whose end state satisfied every required check did know it; grading craft and
grading recall are different axes, and collapsing a passed-but-messy attempt into
the lapse bucket would schedule it as though nothing had been learned. So a pass
floors at `HARD`, and a failure is `AGAIN` outright.

**It returns the facts it used, not a sentence.** `dto.py`'s rule — two very
different adapters read these and whichever formatted first would own the
other's formatting — applies with more force here, because the sentence a panel
wants ("suggested *good*: two hints") is not the sentence a terminal wants. The
domain has no prose except its own refusals.

**Phase 15 changed nothing about the rule, which is the finding.** Interview
mode times an attempt, and the obvious expectation was that a timed attempt
would need its own baseline here. It does not: `AttemptPolicy` derives the
deadline from `estimated_minutes`, which is the number this module has compared
against since Phase 9, so `elapsed > timedelta(minutes=estimated_minutes)` was
*already* the deadline test and an interview's clock was already graded. A
second comparison would have been two spellings of one number.

What did change is one field, and it is the Phase 13 finding not repeated.
`hints_used` is 0 for every interview attempt because no hint was ever on offer,
so a surface reading it alone prints "no hints" as though the solver had shown
restraint — present, correctly formatted and meaningless, which is exactly what
the schedule panel's ease factor was under FSRS (§16). `hints_offered` is the
missing denominator. It also makes honest a case that was always wrong and never
visible: an exercise with no hints at all got the same credit, latent only
because the content suite requires every shipped exercise to have some.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Final

from practice.domain.errors import AttemptStateError
from practice.domain.review import Grade

if TYPE_CHECKING:
    from practice.domain.attempt import Attempt
    from practice.domain.exercise import Exercise

__all__ = ["GradeSuggestion", "suggest_grade"]

#: Best to worst. A penalty walks down this list and stops at the end, which is
#: how "floors at `HARD`" is expressed without a special case: `AGAIN` is not in
#: it, because no number of penalties on a *passed* attempt may reach it.
_SCALE: Final = (Grade.EASY, Grade.GOOD, Grade.HARD)


@dataclass(frozen=True, slots=True)
class GradeSuggestion:
    """The grade, and the three readings that produced it.

    Carried together rather than returned bare so that a surface can show its
    working. A suggestion a solver cannot see the reason for is one they will
    either accept blindly or ignore entirely, and both make the data worse than
    asking them cold.
    """

    grade: Grade
    passed: bool
    advisories: int
    hints_used: int
    overran: bool
    hints_offered: int = 0
    """How many hints this attempt could have revealed.

    The denominator `hints_used` has always needed and never had. Zero means no
    hint was on offer — interview mode withheld them, or the exercise has none —
    and *that* is the case a surface must not describe as restraint.

    Defaulted rather than required because every caller but `suggest_grade`
    constructs one of these in a test, and the field is a reading rather than an
    input: a suggestion built without it is one nobody asked about hints.
    """

    @property
    def penalties(self) -> int:
        """How many of the three readings counted against a passing attempt.

        Unchanged by `hints_offered`, deliberately. Revealing no hint is worth
        no penalty whether or not one was available, so the *grade* was always
        right — it was the explanation that was misleading, and explanations are
        the surface's business.
        """
        return sum((self.advisories > 0, self.hints_used > 0, self.overran))

    @property
    def is_clean(self) -> bool:
        """Passed with no advisory, no hint and inside the estimate."""
        return self.passed and self.penalties == 0

    @property
    def declined_a_hint(self) -> bool:
        """Whether "used no hints" describes a choice the solver made.

        False when none was offered, which is the distinction a sentence like
        "passed clean, no hints" turns on.
        """
        return self.hints_offered > 0 and self.hints_used == 0


def suggest_grade(attempt: Attempt, exercise: Exercise) -> GradeSuggestion:
    """What this attempt looks like, graded.

    Refuses an attempt that has not finished, and the refusal is not defensive
    tidiness: elapsed time is only meaningful once it has stopped running, and a
    verdict is the first of the three inputs. A suggestion about a live attempt
    would be a different number every time it was asked for.
    """
    verdict = attempt.verdict
    finished_at = attempt.finished_at
    if verdict is None or finished_at is None:
        raise AttemptStateError(
            f"cannot suggest a grade for attempt {attempt.id.short}: it is "
            f"{attempt.status.value} and has no verdict"
        )

    advisories = len(verdict.advisories)
    hints_used = attempt.hints_revealed
    # Against the author's own estimate, which is the only baseline the library
    # offers. Deliberately generous in one direction: being *fast* earns nothing
    # extra, because the fast paths through these exercises are often the ones
    # the advisories exist to flag.
    overran = attempt.elapsed(finished_at) > timedelta(
        minutes=exercise.estimated_minutes
    )

    return GradeSuggestion(
        grade=_grade(
            passed=verdict.passed,
            penalties=sum((advisories > 0, hints_used > 0, overran)),
        ),
        passed=verdict.passed,
        advisories=advisories,
        hints_used=hints_used,
        overran=overran,
        # The *policy's* count, not the exercise's: an interview withheld them
        # and a mid-attempt edit cannot retroactively offer them (§4.3).
        hints_offered=attempt.policy.hint_count,
    )


def _grade(*, passed: bool, penalties: int) -> Grade:
    """`AGAIN` for a failure; otherwise one step down the scale per penalty."""
    if not passed:
        return Grade.AGAIN
    return _SCALE[min(penalties, len(_SCALE) - 1)]
