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
repository's: `ExerciseId` sorts `git/...` before `katas/...` and intro before
the rest only by accident. Something better — by difficulty, or by the
prerequisite graph §15 parks — is the curriculum question, and inventing half an
answer to it here would make the real one harder to add.
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

        due = tuple(
            DueExercise(exercise=library[card.exercise_id], card=card, today=today)
            for card in self.reviews.due_on(today)
            if card.exercise_id in library
        )
        unseen = tuple(
            DueExercise(exercise=exercise, card=None, today=today)
            for exercise_id, exercise in library.items()
            if exercise_id not in scheduled
        )
        return due + unseen
