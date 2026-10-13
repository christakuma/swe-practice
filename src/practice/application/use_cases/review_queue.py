"""What to practise today. The question PLAN.md §11 makes Phase 9's exit.

*"'What should I practice today?' is answered by the tool, not by you."* This is
that answer: every exercise whose card has come due, longest-overdue first,
followed by every exercise that has never been scheduled at all.

**The unscheduled half is not a fallback, it is most of the queue.** A store of
due cards is empty on a fresh install with the whole library unpractised — the
one state where the question most needs answering — and it stays empty for every
exercise the solver has never opened. So the queue is a join against the library
rather than a listing of the card table, and `ReviewRepository.cards()` exists
because a method returning only the due subset cannot report an exercise that has
no card to be in it.

**Two queries, each answering its own question.** `due_on(today)` is the indexed
range scan, and its ordering — longest-overdue first — *is* the order of the
queue's first half, so re-deriving it here would be a second opinion about what
"most overdue" means. `cards()` is the set of exercises that have ever been
scheduled, which is the only way to recognise the ones that have not.

**Order inside the new half is the library's**, which is the content
repository's — and as of Phase 11 that is a real order rather than an accident.
It used to be `sorted(ExerciseId)`, which put `git/...` before `katas/...` and
intro before the rest only by coincidence; it is now `content/curriculum.yaml`,
a hand-ordered manifest the content repository reads (ADR 0014). Nothing changed
here to get that, which is the point of having declined to invent half an answer
locally: the queue asks the library for the library's order, and the library's
order got better underneath it.

What is still parked is the prerequisite-graph half of §15 question 4 — unlocking
an exercise only once its predecessors are passed. That needs the attempt history
as an input to the queue, not just the card store, and a hand-ordered list is a
fine answer until someone wants to be stopped rather than merely advised.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.dto import DueExercise

if TYPE_CHECKING:
    from practice.domain.exercise import Exercise
    from practice.domain.ids import ExerciseId
    from practice.domain.ports import Clock, ContentRepository, ReviewRepository

__all__ = ["ReviewQueue"]


@dataclass(frozen=True, slots=True)
class ReviewQueue:
    """Everything worth doing today, in the order worth doing it."""

    content: ContentRepository
    reviews: ReviewRepository
    clock: Clock

    def __call__(self) -> tuple[DueExercise, ...]:
        """Due cards first, then exercises never scheduled.

        An exercise whose card is due but which has since left the library is
        dropped rather than reported: there is nothing to practise, and the row
        would link somewhere that 404s. `OpenAttempt` makes the opposite choice
        for the opposite reason — there, the only thing left to do with a
        stranded attempt is abandon it, and hiding it would hide that too.
        """
        today = self.clock.today()
        library: dict[ExerciseId, Exercise] = {
            exercise.id: exercise for exercise in self.content.list_exercises()
        }
        scheduled = {card.exercise_id for card in self.reviews.cards()}

        # Looked up one at a time rather than in `library`, because a due card
        # may be for a variant: variants are never listed, so never in the
        # unseen half below, but one a solver chose to attempt has a card like
        # any other exercise and comes due like any other (ADR 0028).
        due = tuple(
            DueExercise(exercise=exercise, card=card, today=today)
            for card in self.reviews.due_on(today)
            if (exercise := self.content.get(card.exercise_id)) is not None
        )
        unseen = tuple(
            DueExercise(exercise=exercise, card=None, today=today)
            for exercise_id, exercise in library.items()
            if exercise_id not in scheduled
        )
        return due + unseen
