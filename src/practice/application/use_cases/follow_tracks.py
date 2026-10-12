"""Every track the library offers, walked against the attempt history.

What `/tracks` and the dashboard read: for each track, every step in order, which
of them have been passed and when, and so how far along somebody is.

**All of them at once rather than one by name**, because the two pages that ask
want different amounts and the cost is the same either way. The history is read
once and reduced once; walking four tracks against that reduction is four dict
lookups per step. A second use case taking a name would repeat the read to save
the walk, which is the wrong half to economise on. The page showing a single
track picks it out of this answer, and an unknown name is that page's 404.

**Two reads, like `SummariseProgress`, and for its reason**: the library is
fetched whole because a track is a join from every step to its exercise, and
the alternative is one `content.get` per step.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from practice.application.tracks import follow, records_of

if TYPE_CHECKING:
    from practice.application.tracks import TrackProgress
    from practice.domain.ports import AttemptRepository, ContentRepository

__all__ = ["FollowTracks"]


@dataclass(frozen=True, slots=True)
class FollowTracks:
    """Each declared track with its steps and how many of them are done."""

    content: ContentRepository
    attempts: AttemptRepository

    def __call__(self) -> tuple[TrackProgress, ...]:
        """In the order the library declares them. Empty when it declares none."""
        exercises = {
            exercise.id: exercise for exercise in self.content.list_exercises()
        }
        records = records_of(self.attempts.completed())
        return tuple(
            follow(track, exercises=exercises, records=records)
            for track in self.content.list_tracks()
        )
