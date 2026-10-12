"""Which track an attempt is on, and what the Next button under it offers.

**The track is carried in the URL, and nowhere else.** `/attempt/{id}?track=
blind-75` is the whole of the state: the form that starts an attempt posts the
name, the redirect puts it in the query string, and the two submit forms on the
workbench post it back so the fragment they return knows which track to offer
the next step of. Nothing is stored.

Two alternatives were written down first and the second is the tempting one.
*A column on the attempt* would survive a closed tab, and would put navigation
state — which page somebody happened to arrive from — into an aggregate whose
every other field is about the work, behind a migration and a mapper. *A
remembered "current track"* would make the dashboard able to say "you are on
the Blind 75", and would make two tabs on two tracks fight over one setting,
which is exactly how somebody working through git and katas alternately uses
this. A query string is the one form of the state that is per tab by
construction, visible, bookmarkable, and costs no schema (ADR 0025).

What it costs is that an attempt *resumed from the dashboard* has lost its
track, because that link has no query string. Then the first declared track is
followed, which is the documented default and is the whole library in order —
a worse answer than the right track and a better one than no button.

**A name is checked against the library on the way in and dropped if it names
nothing**, the same rule `routes/browse.py` applies to a filter value and for
its reason: this arrives in a query string somebody can edit and a link
somebody can keep past a rename, and a stale one should cost the track context
rather than the page.

This is a module beside `routes/` rather than one of them because three of them
need it — the workbench page, the kata submission and the scenario submission —
and `attempt` already imports `console`. It is the third module both can point
at, which is the argument `routes/review.py` makes for its own existence.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from practice.composition import Services
    from practice.domain.ids import AttemptId, ExerciseId

__all__ = ["TRACK_FIELD", "known_track", "next_context", "workbench_url"]

#: The query parameter and the form field, which are one name on purpose: a
#: template that reads it from the URL and posts it from a form should not have
#: two spellings to keep in step.
TRACK_FIELD: Final = "track"


def known_track(services: Services, name: str | None) -> str | None:
    """`name` if the library declares a track called that, else `None`.

    Empty counts as absent. The kata submission is posted from JavaScript, which
    always sends the field, so "no track" reaches the server as an empty string
    as often as it does as a missing one.
    """
    if not name:
        return None
    declared = {track.name for track in services.content.list_tracks()}
    return name if name in declared else None


def workbench_url(attempt_id: AttemptId, track_name: str | None) -> str:
    """Where an attempt's page is, with the track it was started on if any.

    Built by hand rather than with `urlencode` because the only value ever
    appended has already been matched against a declared track's name, and
    `Track` refuses a name that is not a lowercase slug.
    """
    base = f"/attempt/{attempt_id}"
    return f"{base}?{TRACK_FIELD}={track_name}" if track_name else base


def next_context(
    services: Services, exercise_id: ExerciseId, track_name: str | None
) -> dict[str, object]:
    """Everything `partials/next.html` reads, for whichever route is rendering it.

    One function for three call sites, because the block under a verdict has to
    be the same block whether the page was loaded or the fragment was swapped
    in — the property `partials/graded.html` exists for.

    `open_by_exercise` comes along for the reason the browse page fetches it:
    the next step may be an exercise with an attempt already open, and starting
    a second one would provision a second workspace and split one piece of work
    across two attempts. The partial offers Resume instead.
    """
    return {
        "next_step": services.next_exercise(exercise_id, track_name),
        "finished_exercise_id": exercise_id,
        "open_by_exercise": {
            found.attempt.exercise_id: found
            for found in services.list_open_attempts()
            if found.can_resume
        },
    }
